"""Security tests for the authentication service (no GUI). Run: pytest -q"""
from __future__ import annotations

import base64

import pyotp
import pytest

from secureapp import config, security
from secureapp.auth import (AuthError, AuthService, PendingEnrollment, PendingLogin, PermissionDenied,
                            RestartRequired, Session, SessionExpired)

ADMIN, ADMIN_PW = "andrea", "correct horse battery staple"


def code(secret: str, clock, offset_steps: int = 0) -> str:
    return pyotp.TOTP(secret).at(clock.now + 30 * offset_steps)


def setup_admin(auth: AuthService, clock) -> tuple[str, list[str], Session]:
    """Complete the first-launch flow; return (totp secret, recovery codes, session)."""
    pending = auth.create_admin(ADMIN, ADMIN_PW)
    secret = pending.totp_secret
    session, recovery = auth.confirm_enrollment(pending, code(secret, clock))
    return secret, recovery, session


def sign_in(auth: AuthService, clock, secret: str, user=ADMIN, pw=ADMIN_PW) -> Session:
    clock.advance(31)  # a new TOTP step, so the code is not a replay
    pending = auth.login_password(user, pw)
    assert isinstance(pending, PendingLogin)
    return auth.verify_otp(pending, code(secret, clock))


# --- first launch -----------------------------------------------------------------------------
def test_first_launch_creates_admin_with_2fa(auth, store, clock):
    assert auth.needs_setup()
    pending = auth.create_admin(ADMIN, ADMIN_PW)
    assert isinstance(pending, PendingEnrollment)
    assert pending.provisioning_uri.startswith("otpauth://totp/SecureApp:andrea?secret=")
    session, recovery = auth.confirm_enrollment(pending, code(pending.totp_secret, clock))
    assert session.role == "admin" and not auth.needs_setup()
    assert len(recovery) == config.RECOVERY_CODE_COUNT and len(set(recovery)) == len(recovery)
    assert pending.totp_secret == "" and pending.key == b""  # secrets dropped from memory
    with pytest.raises(AuthError):
        auth.create_admin("intruder", "another long passphrase")  # only once


def test_secrets_never_stored_in_clear(auth, store, clock):
    secret, recovery, _ = setup_admin(auth, clock)
    row = store.user_by_name(ADMIN)
    assert row["password_hash"].startswith("$argon2id$v=19$m=65536,t=3,p=4$")
    raw = store.path.read_bytes()
    for plain in (ADMIN_PW, secret, *recovery, *(c.replace("-", "") for c in recovery)):
        assert plain.encode() not in raw


def test_database_file_is_private(auth, store):
    assert store.path.stat().st_mode & 0o777 == 0o600


def test_wrong_enrollment_code_and_restart(auth, clock):
    pending = auth.create_admin(ADMIN, ADMIN_PW)
    for _ in range(config.OTP_MAX_ATTEMPTS - 1):
        with pytest.raises(AuthError) as err:
            auth.confirm_enrollment(pending, "000000")
        assert not isinstance(err.value, RestartRequired)
    with pytest.raises(RestartRequired):
        auth.confirm_enrollment(pending, "000000")
    # setup can be resumed by signing in with the password: 2FA is still to be configured
    assert isinstance(auth.login_password(ADMIN, ADMIN_PW), PendingEnrollment)


# --- password policy ----------------------------------------------------------------------------
@pytest.mark.parametrize("weak", [
    "short", "Password2024!", "P@ssw0rd2024", "qwerty123456", "123456789012", "aaaaaaaaaaaaaa",
    "andrea-is-great", "my secureapp pass",
])
def test_weak_passwords_rejected(auth, weak):
    with pytest.raises(AuthError):
        auth.create_admin(ADMIN, weak)


def test_good_passphrase_accepted(auth):
    assert auth.create_admin(ADMIN, "treno per Roma alle 7")


def test_invalid_username_rejected(auth):
    for bad in ("ab", "with space", "x" * 40, "émile"):
        with pytest.raises(AuthError):
            auth.create_admin(bad, ADMIN_PW)


# --- level 1 ----------------------------------------------------------------------------------
def test_password_alone_is_not_enough(auth, clock):
    setup_admin(auth, clock)
    pending = auth.login_password(ADMIN, ADMIN_PW)
    assert isinstance(pending, PendingLogin) and not isinstance(pending, Session)


def test_same_error_for_wrong_password_and_unknown_user(auth, clock):
    setup_admin(auth, clock)
    with pytest.raises(AuthError) as wrong_pw:
        auth.login_password(ADMIN, "not the right passphrase")
    with pytest.raises(AuthError) as unknown:
        auth.login_password("nobody", ADMIN_PW)
    assert str(wrong_pw.value) == str(unknown.value)


def test_username_is_case_insensitive(auth, clock):
    secret, _, _ = setup_admin(auth, clock)
    assert sign_in(auth, clock, secret, user="  Andrea ")


def test_lockout_after_repeated_failures(auth, clock):
    secret, _, _ = setup_admin(auth, clock)
    for _ in range(config.MAX_FAILED_ATTEMPTS - 1):
        with pytest.raises(AuthError):
            auth.login_password(ADMIN, "wrong passphrase here")
    with pytest.raises(RestartRequired, match="Try again in 15 minutes"):
        auth.login_password(ADMIN, "wrong passphrase here")
    with pytest.raises(RestartRequired):  # locked: even the right password is refused
        auth.login_password(ADMIN, ADMIN_PW)
    clock.advance(config.LOCKOUT_SECONDS)
    assert sign_in(auth, clock, secret)


# --- level 2 ----------------------------------------------------------------------------------
@pytest.mark.parametrize("t, expected", [
    (59, "94287082"), (1111111109, "07081804"), (1234567890, "89005924"), (2000000000, "69279037"),
])
def test_totp_matches_rfc6238_test_vectors(t, expected):
    """RFC 6238, Appendix B (HMAC-SHA1): the codes any authenticator app computes.
    The 6-digit code is the last 6 digits of the 8-digit reference value."""
    secret = base64.b32encode(b"12345678901234567890").decode()
    assert security.match_totp(secret, expected[-6:], t, window=0) == t // 30


def test_correct_code_opens_session(auth, clock):
    secret, _, _ = setup_admin(auth, clock)
    session = sign_in(auth, clock, secret)
    assert auth.is_session_valid(session) and session.role == "admin"


def test_code_cannot_be_reused(auth, clock):
    secret, _, _ = setup_admin(auth, clock)
    session = sign_in(auth, clock, secret)
    used = code(secret, clock)
    auth.logout(session)
    clock.advance(1)  # same 30-s step
    pending = auth.login_password(ADMIN, ADMIN_PW)
    with pytest.raises(AuthError, match="already been used"):
        auth.verify_otp(pending, used)
    clock.advance(30)
    assert auth.verify_otp(pending, code(secret, clock))


def test_clock_drift_window(auth, clock):
    secret, _, _ = setup_admin(auth, clock)
    clock.advance(300)
    pending = auth.login_password(ADMIN, ADMIN_PW)
    with pytest.raises(AuthError):
        auth.verify_otp(pending, code(secret, clock, offset_steps=-2))  # 60 s old: refused
    assert auth.verify_otp(pending, code(secret, clock, offset_steps=-1))  # 30 s old: accepted


def test_too_many_wrong_codes_restart_and_lock(auth, clock):
    secret, _, _ = setup_admin(auth, clock)
    clock.advance(31)
    pending = auth.login_password(ADMIN, ADMIN_PW)
    valid = {code(secret, clock, k) for k in (-1, 0, 1)}
    wrong = next(c for c in ("123456", "654321", "111222") if c not in valid)
    for _ in range(config.OTP_MAX_ATTEMPTS - 1):
        with pytest.raises(AuthError) as err:
            auth.verify_otp(pending, wrong)
        assert not isinstance(err.value, RestartRequired)
    with pytest.raises(RestartRequired):
        auth.verify_otp(pending, wrong)
    with pytest.raises(RestartRequired):  # this attempt is over, even with the right code
        auth.verify_otp(pending, code(secret, clock))
    with pytest.raises(RestartRequired, match="Try again"):  # and the account is now locked
        auth.login_password(ADMIN, ADMIN_PW)


def test_pending_login_expires(auth, clock):
    secret, _, _ = setup_admin(auth, clock)
    clock.advance(31)
    pending = auth.login_password(ADMIN, ADMIN_PW)
    clock.advance(config.PENDING_LOGIN_TTL + 1)
    with pytest.raises(RestartRequired, match="expired"):
        auth.verify_otp(pending, code(secret, clock))


def test_recovery_code_works_once(auth, clock):
    secret, recovery, _ = setup_admin(auth, clock)
    pending = auth.login_password(ADMIN, ADMIN_PW)
    assert auth.verify_recovery_code(pending, recovery[0].lower())  # case/dashes tolerated
    pending = auth.login_password(ADMIN, ADMIN_PW)
    with pytest.raises(AuthError):
        auth.verify_recovery_code(pending, recovery[0])


# --- session management -------------------------------------------------------------------------
def test_idle_timeout(auth, clock):
    secret, _, _ = setup_admin(auth, clock)
    session = sign_in(auth, clock, secret)
    clock.advance(config.SESSION_IDLE_TIMEOUT - 1)
    assert auth.touch(session)  # activity restarts the idle timer
    clock.advance(config.SESSION_IDLE_TIMEOUT - 1)
    assert auth.is_session_valid(session)
    clock.advance(2)
    with pytest.raises(SessionExpired):
        auth.check_session(session)
    assert not auth.touch(session)  # an expired session cannot be revived


def test_absolute_timeout(auth, clock):
    secret, _, _ = setup_admin(auth, clock)
    session = sign_in(auth, clock, secret)
    for _ in range(config.SESSION_ABSOLUTE_TIMEOUT // 600):
        clock.advance(600)
        auth.touch(session)
    clock.advance(1)
    assert not auth.is_session_valid(session)


def test_logout_and_forged_session(auth, clock):
    secret, _, _ = setup_admin(auth, clock)
    session = sign_in(auth, clock, secret)
    forged = Session(user_id=session.user_id, username=ADMIN, role="admin", token="guess",
                     created_at=clock.now, last_activity=clock.now)
    assert not auth.is_session_valid(forged)
    auth.logout(session)
    assert not auth.is_session_valid(session)


# --- access control -----------------------------------------------------------------------------
def test_roles_and_permissions(auth, clock):
    secret, _, admin = setup_admin(auth, clock)
    auth.create_user(admin, "mario", "il mio portafoglio 2026", role="user")
    auth.logout(admin)

    clock.advance(31)
    pending = auth.login_password("mario", "il mio portafoglio 2026")
    assert isinstance(pending, PendingEnrollment)  # a new user must set up 2FA first
    mario, _ = auth.confirm_enrollment(pending, code(pending.totp_secret, clock))
    assert mario.role == "user"
    with pytest.raises(PermissionDenied):
        auth.create_user(mario, "eve", "another long passphrase")
    mario.role = "admin"  # tampering with the object grants nothing: role is re-read from the DB
    with pytest.raises(PermissionDenied):
        auth.create_user(mario, "eve", "another long passphrase")


def test_protected_call_requires_session(auth, clock):
    secret, _, admin = setup_admin(auth, clock)
    auth.logout(admin)
    with pytest.raises(SessionExpired):
        auth.create_user(admin, "mario", "il mio portafoglio 2026")


# --- password change ----------------------------------------------------------------------------
def test_change_password_keeps_2fa_working(auth, clock):
    secret, _, admin = setup_admin(auth, clock)
    auth.change_password(admin, ADMIN_PW, "una nuova frase molto lunga")
    auth.logout(admin)
    clock.advance(31)
    with pytest.raises(AuthError):
        auth.login_password(ADMIN, ADMIN_PW)
    assert sign_in(auth, clock, secret, pw="una nuova frase molto lunga")


def test_encrypted_secret_is_bound_to_its_user(auth, store, clock):
    secret, _, admin = setup_admin(auth, clock)
    auth.create_user(admin, "mario", "il mio portafoglio 2026")
    mario_id = store.user_by_name("mario")["id"]
    admin_row = store.user_by_name(ADMIN)
    # an attacker with write access copies the admin's password, salt and secret onto mario
    store.set_password(mario_id, admin_row["password_hash"], admin_row["kdf_salt"], admin_row["totp_secret_enc"])
    with pytest.raises(AuthError, match="damaged"):
        auth.login_password("mario", ADMIN_PW)


def test_audit_log_records_events_without_secrets(auth, store, clock):
    secret, recovery, _ = setup_admin(auth, clock)
    with pytest.raises(AuthError):
        auth.login_password(ADMIN, "wrong passphrase here")
    events = [r["event"] for r in store.audit_events()]
    assert {"ADMIN_CREATED", "TOTP_ENABLED", "LOGIN_OK", "LOGIN_FAILED"} <= set(events)
    dump = " ".join(str(tuple(r)) for r in store.audit_events())
    assert ADMIN_PW not in dump and secret not in dump
