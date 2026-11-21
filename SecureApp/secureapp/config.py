"""Central configuration: app identity, storage location and security policy.

Everything tunable lives here. The PyInstaller spec (app.spec) and build_mac.sh
read APP_NAME, APP_VERSION and BUNDLE_ID from this file, so rename the app here only.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# --- Identity -----------------------------------------------------------------
APP_NAME = "SecureApp"
APP_VERSION = "0.1.0"
BUNDLE_ID = "com.example.secureapp"  # reverse-DNS identifier of the macOS bundle: use your own

# --- Password policy (NIST SP 800-63B-4, §3.1.1.2) ----------------------------
# NIST: minimum 15 characters if the password is the only factor, minimum 8 if it is
# part of multi-factor authentication (our case). 12 is a deliberately safer default.
PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 128  # NIST: allow at least 64

# --- Brute-force protection ---------------------------------------------------
MAX_FAILED_ATTEMPTS = 5  # consecutive failures (password or second factor) before lockout
LOCKOUT_SECONDS = 15 * 60

# --- Second factor: TOTP (RFC 6238), 6 digits every 30 seconds -----------------
TOTP_ISSUER = APP_NAME
TOTP_VALID_WINDOW = 1  # also accept the previous/next 30-s code (clock drift)
OTP_MAX_ATTEMPTS = 5  # wrong codes per sign-in attempt, then back to step 1
PENDING_LOGIN_TTL = 5 * 60  # max seconds between step 1 (password) and step 2 (code)
ENROLLMENT_TTL = 10 * 60  # max seconds to scan the QR code and confirm it
RECOVERY_CODE_COUNT = 8

# --- Session ------------------------------------------------------------------
# OWASP ASVS 4.0.3 level 3 (with 2FA): at most 15 min idle and 12 h overall.
# For high-value data the OWASP Session Management Cheat Sheet cites 2-5 minutes of idle time.
SESSION_IDLE_TIMEOUT = 15 * 60  # sign out after 15 minutes without activity
SESSION_ABSOLUTE_TIMEOUT = 8 * 60 * 60  # hard limit, whatever the activity


def data_dir() -> Path:
    """Per-user writable folder for the database and log file.

    Never inside the .app bundle: the bundle is replaced on every update and is
    covered by its code signature. On macOS: ~/Library/Application Support/<APP_NAME>.
    """
    override = os.environ.get("SECUREAPP_DATA_DIR")
    if override:
        return Path(override).expanduser()
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", str(Path.home())))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
    return base / APP_NAME
