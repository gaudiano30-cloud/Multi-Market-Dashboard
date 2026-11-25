"""TOTP standard RFC 6238 (SHA-1, 6 cifre, intervalli di 30 s)."""
import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote, urlencode

STEP_SECONDS = 30


def create_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def code_at(secret: str, counter: int) -> str:
    padded = secret.upper() + "=" * (-len(secret) % 8)
    key = base64.b32decode(padded, casefold=True)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF)
    return f"{binary % 1_000_000:06d}"


def find_valid_counter(secret: str, code: str, *, now: int | None = None,
                       last_counter: int = -1) -> int | None:
    """Accetta ±1 intervallo per sfasamento orologio; rifiuta codici già usati."""
    if not isinstance(code, str) or len(code) != 6 or not code.isascii() or not code.isdigit():
        return None
    current = int((time.time() if now is None else now) // STEP_SECONDS)
    # Si privilegia l'intervallo corrente; passato/futuro solo per tolleranza.
    for counter in (current, current - 1, current + 1):
        if counter >= 0 and counter > last_counter and hmac.compare_digest(code_at(secret, counter), code):
            return counter
    return None


def provisioning_uri(username: str, secret: str) -> str:
    issuer = "MFE Financial Platform"
    label = f"{issuer}:{username}"
    return f"otpauth://totp/{quote(label, safe='')}?" + urlencode({
        "secret": secret, "issuer": issuer, "algorithm": "SHA1", "digits": 6, "period": STEP_SECONDS
    })
