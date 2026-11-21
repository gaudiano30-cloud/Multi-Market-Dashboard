"""Cryptographic building blocks (no UI, no database).

* Password hashing ....... Argon2id (argon2-cffi), random salt per password
* Key derivation ......... Argon2id raw output with a separate salt
* Secret encryption ...... AES-256-GCM (cryptography)
* Second factor .......... TOTP, RFC 6238 (pyotp)
* Recovery codes ......... 80-bit random codes, only their SHA-256 is stored
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import unicodedata

import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from argon2.low_level import Type, hash_secret_raw
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from . import config

# Argon2id parameters: RFC 9106 "low-memory" profile, above the OWASP minimum
# (19 MiB, t=2, p=1). Fixed explicitly so results never depend on library defaults.
# Do NOT change them once you have users: derive_key() must give the same key forever.
ARGON2_TIME_COST = 3
ARGON2_MEMORY_KIB = 64 * 1024  # 64 MiB
ARGON2_PARALLELISM = 4
ARGON2_HASH_LEN = 32
ARGON2_SALT_LEN = 16

_hasher = PasswordHasher(
    time_cost=ARGON2_TIME_COST,
    memory_cost=ARGON2_MEMORY_KIB,
    parallelism=ARGON2_PARALLELISM,
    hash_len=ARGON2_HASH_LEN,
    salt_len=ARGON2_SALT_LEN,
)


def _normalize(text: str) -> bytes:
    """NFKC-normalise (NIST SP 800-63B) so visually identical passwords always match."""
    return unicodedata.normalize("NFKC", text or "").encode("utf-8")


# --- Passwords -----------------------------------------------------------------
def hash_password(password: str) -> str:
    """Return an encoded Argon2id hash ('$argon2id$v=19$m=65536,t=3,p=4$<salt>$<hash>')."""
    return _hasher.hash(_normalize(password))


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, _normalize(password))
    except (VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


_dummy_hash: str | None = None


def prepare_dummy_hash() -> None:
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = hash_password(secrets.token_urlsafe(24))


def burn_password_check(password: str) -> None:
    """Spend the same time as a real check: used for unknown usernames, so response
    times do not reveal which usernames exist."""
    prepare_dummy_hash()
    verify_password(_dummy_hash or "", password)


# --- Key derivation and encryption ------------------------------------------------
def new_salt() -> bytes:
    return os.urandom(ARGON2_SALT_LEN)


def derive_key(password: str, salt: bytes) -> bytes:
    """32-byte AES-256 key derived from the password (Argon2id, independent salt)."""
    return hash_secret_raw(
        secret=_normalize(password),
        salt=salt,
        time_cost=ARGON2_TIME_COST,
        memory_cost=ARGON2_MEMORY_KIB,
        parallelism=ARGON2_PARALLELISM,
        hash_len=32,
        type=Type.ID,
    )


_NONCE_LEN = 12  # 96-bit nonce, the standard size for AES-GCM


def encrypt(key: bytes, plaintext: bytes, associated_data: bytes) -> bytes:
    """AES-256-GCM. Output = nonce || ciphertext+tag. `associated_data` binds the
    ciphertext to its context (e.g. the user id): moved elsewhere, it will not decrypt."""
    nonce = os.urandom(_NONCE_LEN)
    return nonce + AESGCM(key).encrypt(nonce, plaintext, associated_data)


def decrypt(key: bytes, blob: bytes, associated_data: bytes) -> bytes:
    """Raise cryptography.exceptions.InvalidTag if the key is wrong or the data was altered."""
    return AESGCM(key).decrypt(blob[:_NONCE_LEN], blob[_NONCE_LEN:], associated_data)


# --- Second factor: TOTP (RFC 6238) ------------------------------------------------
TOTP_DIGITS = 6
TOTP_INTERVAL = 30
_CODE_RE = re.compile(r"[0-9]{%d}" % TOTP_DIGITS)


def new_totp_secret() -> str:
    """32 base32 characters = 160 bits, the length recommended by RFC 4226."""
    return pyotp.random_base32()


def totp_provisioning_uri(secret: str, username: str) -> str:
    """otpauth:// URI shown as a QR code to the authenticator app."""
    return pyotp.TOTP(secret, digits=TOTP_DIGITS, interval=TOTP_INTERVAL).provisioning_uri(
        name=username, issuer_name=config.TOTP_ISSUER
    )


def match_totp(secret: str, code: str, now: float, window: int) -> int | None:
    """Return the 30-s time-step whose code equals `code` (searching ±`window` steps
    around `now`), or None. Comparisons are constant-time and the loop never exits early."""
    code = re.sub(r"\s", "", code or "")
    if not _CODE_RE.fullmatch(code):
        return None
    totp = pyotp.TOTP(secret, digits=TOTP_DIGITS, interval=TOTP_INTERVAL)
    current = int(now // TOTP_INTERVAL)
    matched = None
    for step in range(current - window, current + window + 1):
        if hmac.compare_digest(totp.generate_otp(step), code):
            matched = step
    return matched


# --- Recovery codes ----------------------------------------------------------------
_RECOVERY_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # 32 symbols: no 0/O, no 1/I
_RECOVERY_LEN = 16  # 16 symbols x 5 bits = 80 bits of entropy


def new_recovery_codes(count: int) -> list[str]:
    codes = []
    for _ in range(count):
        raw = "".join(secrets.choice(_RECOVERY_ALPHABET) for _ in range(_RECOVERY_LEN))
        codes.append("-".join(raw[i:i + 4] for i in range(0, _RECOVERY_LEN, 4)))
    return codes


def hash_recovery_code(code: str) -> str:
    """A fast hash is adequate here (unlike for passwords): each code carries 80 random
    bits, so trying all of them is out of reach even offline."""
    normalized = re.sub(r"[\s-]", "", code or "").upper()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
