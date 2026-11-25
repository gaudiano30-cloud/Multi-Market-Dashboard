"""Test senza rete né servizi esterni. Eseguire: python -m pytest -q"""
import base64
import tempfile
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from authentication import otp_manager, password_manager
from authentication.auth_service import AuthService, AuthError
from authentication.storage import IdentityStore


def new_service(tmp_path):
    store = IdentityStore(Path(tmp_path) / "auth.sqlite3")
    return AuthService(store, Fernet(Fernet.generate_key()), "test-private-key"), store


def test_argon2_password_hashing():
    hashed = password_manager.hash_password("a-secure-password-long")
    assert hashed.startswith("$argon2id$")
    assert "a-secure-password-long" not in hashed
    assert password_manager.verify_password(hashed, "a-secure-password-long")
    assert not password_manager.verify_password(hashed, "wrong")


def test_totp_standard_vector():
    # RFC6238, SHA-1, 59 secondi: 94287082 ad 8 cifre, 287082 a 6 cifre.
    secret = base64.b32encode(b"12345678901234567890").decode("ascii").rstrip("=")
    assert otp_manager.code_at(secret, 1) == "287082"
    assert otp_manager.find_valid_counter(secret, "287082", now=59) == 1
    assert otp_manager.find_valid_counter(secret, "287082", now=59, last_counter=1) is None


def test_two_steps_registration_login_replay_and_logout(tmp_path, monkeypatch):
    service, store = new_service(tmp_path)
    fixed = 1_800_000_000
    monkeypatch.setattr("authentication.auth_service.time.time", lambda: fixed)
    monkeypatch.setattr("authentication.storage.time.time", lambda: fixed)
    username = "trader_demo"
    password = "very-strong-password-2026"
    user_id = service.register(username, password)
    assert store.get_user(user_id)["active"] == 0
    assert store.get_user(user_id)["otp_secret_encrypted"] != service.setup_details(user_id)[0]

    with pytest.raises(AuthError):
        service.verify_first_factor(username, password, rate_key="pwd")
    secret, uri = service.setup_details(user_id)
    assert uri.startswith("otpauth://totp/")
    setup_code = otp_manager.code_at(secret, fixed // 30)
    token1 = service.verify_second_factor(user_id, setup_code, activate=True, rate_key="otp", now=fixed)
    assert store.current_user(token1, now=fixed)["username"] == username
    service.logout(token1)
    assert store.current_user(token1, now=fixed) is None

    with pytest.raises(AuthError):
        service.verify_first_factor(username, "wrong-password", rate_key="pwd")
    assert service.verify_first_factor(username, password, rate_key="pwd") == user_id
    # Lo stesso codice non può essere riutilizzato.
    with pytest.raises(AuthError):
        service.verify_second_factor(user_id, setup_code, activate=False, rate_key="otp", now=fixed)
    fixed += 30
    second_code = otp_manager.code_at(secret, fixed // 30)
    token2 = service.verify_second_factor(user_id, second_code, activate=False, rate_key="otp", now=fixed)
    assert store.current_user(token2, now=fixed) is not None
    assert store.current_user(token2, now=fixed + 1801) is None


def test_duplicate_user(tmp_path):
    service, _ = new_service(tmp_path)
    service.register("example", "secure-secret-long-1")
    with pytest.raises(AuthError):
        service.register("EXAMPLE", "secure-secret-long-2")


def test_limited_failed_attempts(tmp_path):
    service, store = new_service(tmp_path)
    key = "remote-client"
    for i in range(12):
        store.record_failed_attempt(key, limit=12, now=1_800_000_000)
    assert store.is_limited(key, now=1_800_000_010)
    assert not store.is_limited(key, now=1_800_001_000)


def test_session_expiry_absolute(tmp_path):
    _, store = new_service(tmp_path)
    with store.connection() as db:
        db.execute("INSERT INTO users(username,password_hash,otp_secret_encrypted,active,created_at) VALUES(?,?,?,?,?)",
                   ("test", "hash", "secret", 1, 1))
    token = store.create_session(1, now=100)
    assert store.current_user(token, now=100) is not None
    assert store.current_user(token, now=100 + 8*3600) is None
