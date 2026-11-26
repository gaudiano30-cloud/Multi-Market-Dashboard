"""
Password Management Module.

This module is responsible for the secure handling of user
passwords through the Argon2id password hashing algorithm.

Its main responsibilities include:
    - Generating secure password hashes.
    - Using a randomly generated salt for each hash.
    - Verifying passwords against previously stored hashes.
    - Checking whether existing hashes require an update
      following changes in security parameters.

The module centralizes password hashing configuration
and ensures that authentication can be performed without
storing or recovering plaintext passwords.

It provides reusable password management functions to
the authentication service.
"""

from argon2 import (
    PasswordHasher,
    Type,
)  # due elementi della libreria argon2 (non è una libreria standard ma  deve essere installata da terminale)
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# creiamo un'stanza della classe PasswordHasher, specificando i parametri che determinano il funzionamento dell'algoritmo
_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2, hash_len=32, salt_len=16, type=Type.ID)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(encoded: str, password: str) -> bool:
    try:
        return _hasher.verify(encoded, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError, TypeError, ValueError):
        return False


def needs_rehash(encoded: str) -> bool:
    return _hasher.check_needs_rehash(encoded)
