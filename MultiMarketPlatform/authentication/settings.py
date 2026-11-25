"""Configurazione centralizzata; instance/ non va versionata."""
import base64
import hashlib
import os
import secrets
from pathlib import Path
from cryptography.fernet import Fernet

ROOT = Path(__file__).resolve().parent.parent
INSTANCE = ROOT / "instance"
DB_PATH = ROOT / "database" / "users_auth.sqlite3"
SECRET_PATH = INSTANCE / ".flask-secret"
SESSION_IDLE_SECONDS = 30 * 60
SESSION_MAX_SECONDS = 8 * 60 * 60
SIGNIN_CHALLENGE_SECONDS = 5 * 60
SIGNUP_CHALLENGE_SECONDS = 15 * 60


def load_secret_key() -> str:
    """Chiave permanente da variabile d'ambiente oppure file privato 0600."""
    INSTANCE.mkdir(parents=True, exist_ok=True)
    configured = os.environ.get("MFE_SECRET_KEY")
    if configured:
        if len(configured) < 32:
            raise RuntimeError("MFE_SECRET_KEY deve contenere almeno 32 caratteri casuali.")
        return configured
    try:
        fd = os.open(str(SECRET_PATH), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        pass
    else:
        with os.fdopen(fd, "w", encoding="ascii") as stream:
            stream.write(secrets.token_urlsafe(48))
    if os.name == "posix":
        SECRET_PATH.chmod(0o600)
    return SECRET_PATH.read_text(encoding="ascii").strip()


def secret_cipher(key: str) -> Fernet:
    # Derivazione separata dalla chiave di firma cookie.
    raw = hashlib.sha256(("mfe-totp-secret-v1:" + key).encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(raw))
