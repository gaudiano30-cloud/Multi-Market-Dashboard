"""
Authentication Service Module.

This module implements the core authentication and security
logic of the application, independently of the user interface.

Its main responsibilities include:
    - User registration and credential validation.
    - Secure password hashing and verification.
    - OTP secret generation, encryption and verification.
    - Two-factor authentication (2FA).
    - Account activation.
    - Rate limiting and temporary account locking.
    - Protection against OTP reuse.
    - User session creation, identification and revocation.

The AuthService class coordinates the interaction between
the database, password manager, OTP manager and session
manager, providing a centralized and reusable authentication
service for both web and command-line interfaces.
"""

import hashlib  # libreria standard di Python che permette di utilizzare funzioni di hashing

# hashlib viene utilizzato per generare identificativi associati ai tentativi di accesso, non per effettuare l'hashing delle password che invece sono gestite separatamente da password_manager.py
import re  # Regular Expressions
import sqlite3  # libreria standard di Python che permette di interagire con un database SQLite attraverso il linguaggio SQL.
import time

from cryptography.fernet import InvalidToken

# cryptography è una libreria Python esterna dedicata alla sicurezza informatica
# Fernet è un sistema di crittografia simmetrica: utilizza una chiave segreta per criptare e decriptare informazioni, verificando anche l'integrità dei dati criptati
# Invalid Token = Questa eccezione può verificarsi quando tentiamo di decriptare un'informazione che non può essere validata o recuperata correttamente, per esempio perché utilizziamo una chiave sbagliata.
from . import otp_manager, password_manager
from .settings import SIGNUP_CHALLENGE_SECONDS
from .session_manager import SessionManager


class AuthError(Exception):
    """Errore controllato, mostrabile senza esporre dati di sicurezza."""


class AuthService:
    def __init__(self, store, cipher, server_secret):  # self = l'istanza della classe che stiamo inizializzando
        self.store = store  # oggetto attraverso cui accediamo ai dati
        self.sessions = SessionManager(store)  # creiamo
        self.cipher = cipher  # oggetto che permette di criptare e decriptare
        self.server_secret = server_secret  # valore segreto utilizzato dal server
        # Stesso costo di hashing per account inesistenti.
        self._dummy_hash = password_manager.hash_password("no-user-password")

    # Il rate limiting è un meccanismo che limita il numero di operazioni che un utente o un client può effettuare in un determinato intervallo di tempo.
    def client_rate_key(self, category, ip_address):
        raw = f"{self.server_secret}:rate:{category}:{ip_address}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def assert_not_limited(self, key):
        if self.store.is_limited(key):
            raise AuthError("Too many attempts. Try again in 15 minutes.")

    # funzione che si occupa del processo di registrazione di un nuovo utente
    def register(self, username, password, *, rate_key=None):
        if rate_key:
            self.assert_not_limited(rate_key)
        if not isinstance(username, str) or not re.fullmatch(
            r"[A-Za-z0-9_.-]{3,32}", username
        ):  # controlla che username sia una stringa e username rispetti il pattern
            raise AuthError("Username must have 3 to 32 caratteri; lettere, numeri, punto, _ o -.")
        if (
            not isinstance(password, str) or len(password) < 12 or len(password) > 128
        ):  # Verifichiamo che la password sia una stringa di lunghezza compresa tra 12 e 128 caratteri, estremi inclusi.
            raise AuthError("Invalid password: da 12 a 128 caratteri.")

        # Generiamo il segreto OTP associato al nuovo utente.
        secret = otp_manager.create_secret()
        # comando seguente cripta il segreto OTP prima di salvarlo nel database
        encrypted = self.cipher.encrypt(secret.encode("ascii")).decode("ascii")
        encoded = password_manager.hash_password(password)  # effettuiamo l'hashing della password
        try:
            user_id = self.store.insert_user(username, encoded, encrypted)
        except (
            sqlite3.IntegrityError
        ):  # errore si verifica quando un'operazione viola un vincolo di integrità del database, per esempio un vincolo che impedisce di avere due utenti con lo stesso username.
            raise AuthError("Username already taken!") from None
        if rate_key:
            # Al massimo 10 account da uno stesso IP per ora.
            self.store.record_failed_attempt(rate_key, limit=10, window=3600, block=3600)
        return user_id

    def setup_details(self, user_id, *, now=None):
        now = int(time.time() if now is None else now)
        row = self.store.get_user(user_id)
        if not row or row["active"] or now - row["created_at"] >= SIGNUP_CHALLENGE_SECONDS:
            raise AuthError("Registration session expired. Go back to Sign up.")
        try:
            secret = self.cipher.decrypt(row["otp_secret_encrypted"].encode("ascii")).decode("ascii")
        except (InvalidToken, ValueError):
            raise AuthError("Impossibile recuperare il segreto OTP.") from None
        return secret, otp_manager.provisioning_uri(row["username"], secret)

    def verify_first_factor(self, username, password, *, rate_key):
        self.assert_not_limited(rate_key)
        # Evita tentativi con password giganti che sovraccaricherebbero Argon2.
        if (
            not isinstance(password, str)
            or len(password) > 128
            or not isinstance(username, str)
            or len(username) > 64
        ):
            self.store.record_failed_attempt(rate_key)
            raise AuthError("Credenziali non valide.")
        row = self.store.get_user_by_name(username)
        encoded = row["password_hash"] if row else self._dummy_hash
        matched = password_manager.verify_password(encoded, password)
        now = int(time.time())
        if not row or not matched or not row["active"] or row["password_locked_until"] > now:
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
