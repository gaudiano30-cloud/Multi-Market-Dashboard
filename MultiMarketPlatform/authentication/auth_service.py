"""Regole di sicurezza applicate da web/CLI e indipendenti dalla UI."""
import hashlib
import re
import sqlite3
import time

from cryptography.fernet import InvalidToken
from . import otp_manager, password_manager
from .settings import SIGNUP_CHALLENGE_SECONDS
from .session_manager import SessionManager


class AuthError(Exception):
    """Errore controllato, mostrabile senza esporre dati di sicurezza."""


class AuthService:
    def __init__(self, store, cipher, server_secret):
        self.store = store
        self.sessions = SessionManager(store)
        self.cipher = cipher
        self.server_secret = server_secret
        # Stesso costo di hashing per account inesistenti.
        self._dummy_hash = password_manager.hash_password("no-user-password")

    def client_rate_key(self, category, ip_address):
        raw = f"{self.server_secret}:rate:{category}:{ip_address}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def assert_not_limited(self, key):
        if self.store.is_limited(key):
            raise AuthError("Troppi tentativi. Riprova tra circa 15 minuti.")

    def register(self, username, password, *, rate_key=None):
        if rate_key:
            self.assert_not_limited(rate_key)
        if not isinstance(username, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{3,32}", username):
            raise AuthError("Username: 3-32 caratteri; lettere, numeri, punto, _ o -.")
        if not isinstance(password, str) or len(password) < 12 or len(password) > 128:
            raise AuthError("Password: da 12 a 128 caratteri.")
        secret = otp_manager.create_secret()
        encrypted = self.cipher.encrypt(secret.encode("ascii")).decode("ascii")
        encoded = password_manager.hash_password(password)
        try:
            user_id = self.store.insert_user(username, encoded, encrypted)
        except sqlite3.IntegrityError:
            raise AuthError("Username già utilizzato.") from None
        if rate_key:
            # Al massimo 10 account da uno stesso IP per ora.
            self.store.record_failed_attempt(rate_key, limit=10, window=3600, block=3600)
        return user_id

    def setup_details(self, user_id, *, now=None):
        now = int(time.time() if now is None else now)
        row = self.store.get_user(user_id)
        if not row or row["active"] or now - row["created_at"] >= SIGNUP_CHALLENGE_SECONDS:
            raise AuthError("Registrazione scaduta. Riparti da Sign up.")
        try:
            secret = self.cipher.decrypt(row["otp_secret_encrypted"].encode("ascii")).decode("ascii")
        except (InvalidToken, ValueError):
            raise AuthError("Impossibile recuperare il segreto OTP.") from None
        return secret, otp_manager.provisioning_uri(row["username"], secret)

    def verify_first_factor(self, username, password, *, rate_key):
        self.assert_not_limited(rate_key)
        # Evita tentativi con password giganti che sovraccaricherebbero Argon2.
        if not isinstance(password, str) or len(password) > 128 or not isinstance(username, str) or len(username) > 64:
            self.store.record_failed_attempt(rate_key)
            raise AuthError("Credenziali non valide.")
        row = self.store.get_user_by_name(username)
        encoded = row["password_hash"] if row else self._dummy_hash
        matched = password_manager.verify_password(encoded, password)
        now = int(time.time())
        if (not row or not matched or not row["active"] or row["password_locked_until"] > now):
            if row and not matched:
                self.store.password_failure(row["id"], now=now)
            self.store.record_failed_attempt(rate_key, now=now)
            raise AuthError("Credenziali non valide o account temporaneamente bloccato.")
        self.store.password_success(row["id"])
        self.store.clear_failed_attempts(rate_key)
        if password_manager.needs_rehash(encoded):
            self.store.update_password_hash(row["id"], password_manager.hash_password(password))
        return row["id"]

    def verify_second_factor(self, user_id, code, *, activate=False, rate_key, now=None):
        self.assert_not_limited(rate_key)
        now = int(time.time() if now is None else now)
        row = self.store.get_user(user_id)
        if not row or bool(row["active"]) == bool(activate) or row["otp_locked_until"] > now:
            raise AuthError("Verifica non disponibile. Riparti dall'accesso.")
        if activate and now - row["created_at"] >= SIGNUP_CHALLENGE_SECONDS:
            raise AuthError("Registrazione scaduta. Riparti da Sign up.")
        try:
            secret = self.cipher.decrypt(row["otp_secret_encrypted"].encode("ascii")).decode("ascii")
        except (InvalidToken, ValueError):
            raise AuthError("Verifica non disponibile.") from None
        counter = otp_manager.find_valid_counter(secret, code, now=now, last_counter=row["last_otp_counter"])
        if counter is None or not self.store.consume_otp(user_id, counter, activate=activate, now=now):
            self.store.otp_failure(user_id, now=now)
            self.store.record_failed_attempt(rate_key, limit=8, now=now)
            raise AuthError("Codice non valido, già utilizzato oppure scaduto.")
        self.store.clear_failed_attempts(rate_key)
        return self.sessions.issue(user_id, now=now)

    def current_user(self, token):
        return self.sessions.identify(token)

    def logout(self, token):
        self.sessions.revoke(token)
