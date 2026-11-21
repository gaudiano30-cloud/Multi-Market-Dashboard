"""`SecureApp --selftest`: check, without opening any window, that every library
works inside the packaged app (PyInstaller sometimes misses a hidden dependency)."""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path


def _check(condition: bool, what: str) -> None:
    if not condition:
        raise RuntimeError(f"check failed: {what}")


def run_selftest() -> int:
    try:
        import pyotp
        import qrcode
        from PySide6 import QtCore, QtGui, QtWidgets

        _check(hasattr(QtWidgets, "QMainWindow") and hasattr(QtGui, "QImage"), "Qt libraries")
        from . import security
        from .auth import AuthService
        from .storage import Store

        stored = security.hash_password("selftest passphrase")
        _check(security.verify_password(stored, "selftest passphrase"), "Argon2id hash/verify")
        key = security.derive_key("selftest passphrase", security.new_salt())
        _check(security.decrypt(key, security.encrypt(key, b"ok", b"ctx"), b"ctx") == b"ok", "AES-256-GCM")
        secret = security.new_totp_secret()
        _check(security.match_totp(secret, pyotp.TOTP(secret).now(), time.time(), 1) is not None, "TOTP")
        qr = qrcode.QRCode()
        qr.add_data(security.totp_provisioning_uri(secret, "selftest"))
        qr.make(fit=True)
        _check(len(qr.get_matrix()) > 20, "QR code")
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "selftest.db")
            _check(AuthService(store).needs_setup(), "SQLite storage")
            store.close()
    except Exception as exc:  # noqa: BLE001
        print(f"SELFTEST FAILED: {exc!r}", file=sys.stderr)
        return 1
    print(f"SELFTEST OK (Python {sys.version.split()[0]}, Qt {QtCore.qVersion()})")
    return 0
