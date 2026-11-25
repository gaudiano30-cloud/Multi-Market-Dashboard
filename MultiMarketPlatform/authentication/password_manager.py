"""Password: Argon2id, salt casuale per hash, niente password in chiaro."""
from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# Parametri controllabili centralmente e aggiornabili senza cambiare il DB.
_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2,
                         hash_len=32, salt_len=16, type=Type.ID)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(encoded: str, password: str) -> bool:
    try:
        return _hasher.verify(encoded, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError, TypeError, ValueError):
        return False


def needs_rehash(encoded: str) -> bool:
    return _hasher.check_needs_rehash(encoded)
