"""Authentication service: the single gatekeeper between the UI and the data.

    First launch    create_admin() ──► confirm_enrollment() ──► Session
    Every launch    login_password()            level 1: username + password
                        └─► verify_otp()  or  verify_recovery_code()   level 2 ──► Session
    Signed in       check_session(), touch(), logout(), methods decorated with @requires(...)

The UI only displays what this service returns: it can never "skip" a level, because
a Session object is created exclusively by _finish_login(), after both factors.
"""
from __future__ import annotations

import functools
import hmac
import math
import secrets
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Callable, NoReturn

from cryptography.exceptions import InvalidTag

from . import config, policy, security
from .storage import Store

# Role -> permissions. Deny by default: an unknown role has no permissions.
ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "admin": frozenset({"users.manage", "data.read", "data.write"}),
    "user": frozenset({"data.read", "data.write"}),
    "viewer": frozenset({"data.read"}),
}

GENERIC_LOGIN_ERROR = "Incorrect username or password."  # same text whatever was wrong


class AuthError(Exception):
    """Expected failure. The message is safe to show to the user."""


class RestartRequired(AuthError):
    """The current sign-in attempt is over (expired, too many errors, account locked)."""


class SessionExpired(AuthError):
    """There is no valid session: the user has to sign in again."""


class PermissionDenied(AuthError):
    """The signed-in user's role does not grant the required permission."""


@dataclass
class Session:
    user_id: int
    username: str
    role: str
    token: str = field(repr=False)
    created_at: float
    last_activity: float


@dataclass
class _Pending:
    user_id: int
    username: str
    role: str
    totp_secret: str = field(repr=False)
    expires_at: float
    attempts: int = 0
    active: bool = True

    def close(self) -> None:
        """End this attempt and drop the secrets it holds in memory."""
        self.active = False
        self.totp_secret = ""


@dataclass
class PendingLogin(_Pending):
    """Password verified: waiting for the second factor."""


@dataclass
class PendingEnrollment(_Pending):
    """Password verified (or account just created): waiting for the first TOTP code."""

    key: bytes = field(default=b"", repr=False)  # derived from the password, encrypts the secret

    @property
    def provisioning_uri(self) -> str:
        return security.totp_provisioning_uri(self.totp_secret, self.username)

    def close(self) -> None:
        super().close()
        self.key = b""


def requires(permission: str) -> Callable:
    """Protect an AuthService method whose first argument is the caller's Session.

    The role is re-read from the database on every call, so a role change takes
    effect immediately and a tampered Session object cannot grant itself rights.
    """

    def decorator(method: Callable) -> Callable:
        @functools.wraps(method)
        def wrapper(self: "AuthService", session: Session, *args, **kwargs):
            active = self.check_session(session)
            user = self._store.user_by_id(active.user_id)
            role = user["role"] if user is not None else ""
            if permission not in ROLE_PERMISSIONS.get(role, frozenset()):
                self._store.audit("ACCESS_DENIED", active.username, f"{method.__name__} requires {permission}")
                raise PermissionDenied("Your role does not allow this action.")
            self.touch(session)
            return method(self, session, *args, **kwargs)

        return wrapper

    return decorator


class AuthService:
    def __init__(self, store: Store, clock: Callable[[], float] = time.time,
                 monotonic: Callable[[], float] = time.monotonic) -> None:
        self._store = store
        self._clock = clock  # wall clock: TOTP codes and lockouts (stored on disk)
        self._monotonic = monotonic  # monotonic clock: session and attempt timeouts
        self._active: Session | None = None
        security.prepare_dummy_hash()

    # ==== First launch =================================================================
    def needs_setup(self) -> bool:
        return self._store.count_users() == 0

    def create_admin(self, username: str, password: str) -> PendingEnrollment:
        if not self.needs_setup():
            raise AuthError("An administrator already exists.")
        user = self._create_user_row(username, password, "admin")
        self._store.audit("ADMIN_CREATED", user["username"])
        return self._begin_enrollment(user, password)

    def confirm_enrollment(self, pending: PendingEnrollment, code: str) -> tuple[Session, list[str]]:
        """Check the first code from the authenticator app, then activate 2FA.
        Returns the new session and the recovery codes (shown once, stored only as hashes)."""
        user = self._pending_user(pending)
        step = security.match_totp(pending.totp_secret, code, self._clock(), config.TOTP_VALID_WINDOW)
        if step is None:
            pending.attempts += 1
            if pending.attempts >= config.OTP_MAX_ATTEMPTS:
                pending.close()
                raise RestartRequired("Too many invalid codes. Start the setup again.")
            raise AuthError("Invalid code. Make sure the phone sets its time automatically, then retry.")
        secret_enc = security.encrypt(pending.key, pending.totp_secret.encode(), self._aad(user["id"]))
        codes = security.new_recovery_codes(config.RECOVERY_CODE_COUNT)
        self._store.enable_totp(user["id"], secret_enc, step, [security.hash_recovery_code(c) for c in codes])
        self._store.audit("TOTP_ENABLED", user["username"])
        return self._finish_login(pending, user, "2FA setup"), codes

    # ==== Level 1: username + password ====================================================
    def login_password(self, username: str, password: str) -> PendingLogin | PendingEnrollment:
        name = policy.normalize_username(username)
        user = self._store.user_by_name(name) if name else None
        if user is None:
            security.burn_password_check(password)  # same cost as a real check
            self._store.audit("LOGIN_FAILED", name or None, "unknown username")
            raise AuthError(GENERIC_LOGIN_ERROR)

        now = self._clock()
        if user["locked_until"] > now:
            self._store.audit("LOGIN_BLOCKED", name, "account locked")
            raise RestartRequired(self._lock_message(user["locked_until"] - now))

        if not security.verify_password(user["password_hash"], password):
            self._register_failure(user, "wrong password", GENERIC_LOGIN_ERROR)

        if security.password_needs_rehash(user["password_hash"]):  # parameters were raised
            self._store.set_password_hash(user["id"], security.hash_password(password))
        self._store.audit("PASSWORD_OK", name)

        if user["totp_secret_enc"] is None:  # 2FA not set up yet (e.g. account made by an admin)
            return self._begin_enrollment(user, password)

        key = security.derive_key(password, user["kdf_salt"])
        try:
            secret = security.decrypt(key, user["totp_secret_enc"], self._aad(user["id"])).decode()
        except InvalidTag:
            self._store.audit("TOTP_UNREADABLE", name)
            raise AuthError("The two-factor configuration is damaged. Contact the administrator.") from None
        return PendingLogin(user_id=user["id"], username=name, role=user["role"], totp_secret=secret,
                            expires_at=self._monotonic() + config.PENDING_LOGIN_TTL)

    # ==== Level 2: one-time code ============================================================
    def verify_otp(self, pending: PendingLogin, code: str) -> Session:
        user = self._pending_user(pending)
        step = security.match_totp(pending.totp_secret, code, self._clock(), config.TOTP_VALID_WINDOW)
        if step is None:
            self._second_factor_failure(pending, user, "wrong code", "Invalid code. Please try again.")
        if not self._store.advance_totp_step(user["id"], step):
            self._second_factor_failure(pending, user, "code reused",
                                        "This code has already been used. Wait for the next one.")
        return self._finish_login(pending, user, "authenticator code")

    def verify_recovery_code(self, pending: PendingLogin, code: str) -> Session:
        user = self._pending_user(pending)
        if not self._store.consume_recovery_code(user["id"], security.hash_recovery_code(code)):
            self._second_factor_failure(pending, user, "wrong recovery code",
                                        "Invalid or already used recovery code.")
        left = self._store.unused_recovery_codes(user["id"])
        return self._finish_login(pending, user, f"recovery code ({left} left)")

    # ==== Session management ==================================================================
    def check_session(self, session: Session | None) -> Session:
        """Return the active session, or raise SessionExpired."""
        active = self._active
        if session is None or active is None or not hmac.compare_digest(session.token, active.token):
            raise SessionExpired("You are not signed in.")
        now = self._monotonic()
        if (now - active.last_activity > config.SESSION_IDLE_TIMEOUT
                or now - active.created_at > config.SESSION_ABSOLUTE_TIMEOUT):
            self._end_session("SESSION_EXPIRED")
            raise SessionExpired("Your session has expired. Please sign in again.")
        return active

    def is_session_valid(self, session: Session | None) -> bool:
        try:
            self.check_session(session)
            return True
        except SessionExpired:
            return False

    def touch(self, session: Session | None) -> bool:
        """Record user activity (restarts the idle timer). False if the session is over."""
        try:
            active = self.check_session(session)
        except SessionExpired:
            return False
        active.last_activity = self._monotonic()
        return True

    def logout(self, session: Session | None) -> None:
        active = self._active
        if active is not None and session is not None and hmac.compare_digest(session.token, active.token):
            self._end_session("LOGOUT")

    # ==== Protected operations (examples of access control) ===================================
    @requires("users.manage")
    def create_user(self, session: Session, username: str, password: str, role: str = "user") -> int:
        """Admin only. The new user sets up 2FA at their first sign-in."""
        if role not in ROLE_PERMISSIONS:
            raise AuthError(f"Unknown role: {role}")
        user = self._create_user_row(username, password, role)
        self._store.audit("USER_CREATED", session.username, f"{user['username']} ({role})")
        return user["id"]

    def change_password(self, session: Session, current: str, new: str) -> None:
        active = self.check_session(session)
        user = self._store.user_by_id(active.user_id)
        if not security.verify_password(user["password_hash"], current):
            self._store.audit("PASSWORD_CHANGE_FAILED", user["username"], "wrong current password")
            raise AuthError("The current password is not correct.")
        self._validate_password(new, user["username"])
        salt = security.new_salt()
        secret_enc = user["totp_secret_enc"]
        if secret_enc is not None:  # re-encrypt the TOTP secret with the key of the new password
            secret = security.decrypt(security.derive_key(current, user["kdf_salt"]), secret_enc,
                                      self._aad(user["id"]))
            secret_enc = security.encrypt(security.derive_key(new, salt), secret, self._aad(user["id"]))
        self._store.set_password(user["id"], security.hash_password(new), salt, secret_enc)
        self._store.audit("PASSWORD_CHANGED", user["username"])
        self.touch(session)

    # ==== Internals =================================================================================
    @staticmethod
    def _aad(user_id: int) -> bytes:
        # Binds the encrypted TOTP secret to its user row. Constant on purpose (not APP_NAME).
        return b"totp-secret:v1:" + str(user_id).encode()

    @staticmethod
    def _validate_password(password: str, username: str) -> None:
        problems = policy.password_problems(password, username)
        if problems:
            raise AuthError(" ".join(problems))

    @staticmethod
    def _lock_message(seconds: float) -> str:
        minutes = max(1, math.ceil(seconds / 60))
        return f"Too many failed attempts. Try again in {minutes} minute{'s' if minutes != 1 else ''}."

    def _create_user_row(self, username: str, password: str, role: str) -> sqlite3.Row:
        name = policy.normalize_username(username)
        problem = policy.username_problem(name)
        if problem:
            raise AuthError(problem)
        self._validate_password(password, name)
        try:
            user_id = self._store.add_user(name, role, security.hash_password(password), security.new_salt())
        except sqlite3.IntegrityError:
            raise AuthError("This username is already taken.") from None
        return self._store.user_by_id(user_id)

    def _begin_enrollment(self, user: sqlite3.Row, password: str) -> PendingEnrollment:
        return PendingEnrollment(
            user_id=user["id"], username=user["username"], role=user["role"],
            totp_secret=security.new_totp_secret(),
            expires_at=self._monotonic() + config.ENROLLMENT_TTL,
            key=security.derive_key(password, user["kdf_salt"]),
        )

    def _pending_user(self, pending: _Pending | None) -> sqlite3.Row:
        if pending is None or not pending.active:
            raise RestartRequired("Please sign in again.")
        if self._monotonic() > pending.expires_at:
            pending.close()
            raise RestartRequired("The sign-in attempt has expired. Please sign in again.")
        user = self._store.user_by_id(pending.user_id)
        if user is None:
            pending.close()
            raise RestartRequired("Please sign in again.")
        now = self._clock()
        if user["locked_until"] > now:
            pending.close()
            raise RestartRequired(self._lock_message(user["locked_until"] - now))
        return user

    def _register_failure(self, user: sqlite3.Row, reason: str, message: str) -> NoReturn:
        now = self._clock()
        updated = self._store.register_failure(user["id"], now, config.MAX_FAILED_ATTEMPTS, config.LOCKOUT_SECONDS)
        self._store.audit("LOGIN_FAILED", user["username"], reason)
        if updated["locked_until"] > now:
            self._store.audit("ACCOUNT_LOCKED", user["username"], f"{config.MAX_FAILED_ATTEMPTS} failures in a row")
            raise RestartRequired(self._lock_message(updated["locked_until"] - now))
        raise AuthError(message)

    def _second_factor_failure(self, pending: _Pending, user: sqlite3.Row, reason: str, message: str) -> NoReturn:
        pending.attempts += 1
        try:
            self._register_failure(user, reason, message)
        except RestartRequired:
            pending.close()
            raise
        except AuthError:
            if pending.attempts >= config.OTP_MAX_ATTEMPTS:
                pending.close()
                raise RestartRequired("Too many invalid codes. Please sign in again.") from None
            raise

    def _finish_login(self, pending: _Pending, user: sqlite3.Row, method: str) -> Session:
        """The only place where a Session is created: both factors have been verified."""
        pending.close()
        self._store.mark_login(user["id"])
        self._store.audit("LOGIN_OK", user["username"], method)
        now = self._monotonic()
        self._active = Session(user_id=user["id"], username=user["username"], role=user["role"],
                               token=secrets.token_urlsafe(32), created_at=now, last_activity=now)
        return self._active

    def _end_session(self, event: str) -> None:
        if self._active is not None:
            self._store.audit(event, self._active.username)
            self._active.token = ""
            self._active = None
