"""Repository SQLite esclusivamente per identità, rate limit e sessioni.

Non contiene prezzi, strumenti o dati finanziari.
"""
from contextlib import contextmanager
import hashlib
import secrets
import sqlite3
import time
from pathlib import Path

from .settings import SESSION_IDLE_SECONDS, SESSION_MAX_SECONDS, SIGNUP_CHALLENGE_SECONDS


class IdentityStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connection(self):
        connection = sqlite3.connect(str(self.path), timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=15000")
        try:
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self):
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    password_hash TEXT NOT NULL,
                    otp_secret_encrypted TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 0 CHECK (active IN (0, 1)),
                    created_at INTEGER NOT NULL,
                    last_otp_counter INTEGER NOT NULL DEFAULT -1,
                    failed_password INTEGER NOT NULL DEFAULT 0,
                    password_locked_until INTEGER NOT NULL DEFAULT 0,
                    failed_otp INTEGER NOT NULL DEFAULT 0,
                    otp_locked_until INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    created_at INTEGER NOT NULL,
                    last_seen INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
                CREATE TABLE IF NOT EXISTS rate_limits (
                    rate_key TEXT PRIMARY KEY,
                    window_start INTEGER NOT NULL,
                    failures INTEGER NOT NULL,
                    blocked_until INTEGER NOT NULL DEFAULT 0
                );
            """)

    @staticmethod
    def _dict(row):
        return dict(row) if row is not None else None

    def get_user_by_name(self, username):
        with self.connection() as db:
            return self._dict(db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone())

    def get_user(self, user_id):
        with self.connection() as db:
            return self._dict(db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone())

    def insert_user(self, username, hashed_password, encrypted_secret, *, now=None):
        now = int(time.time() if now is None else now)
        with self.connection() as db:
            # Libera soltanto username mai attivati e scaduti.
            db.execute("DELETE FROM users WHERE active=0 AND created_at<?",
                       (now - SIGNUP_CHALLENGE_SECONDS,))
            cur = db.execute(
                "INSERT INTO users(username,password_hash,otp_secret_encrypted,created_at) VALUES (?,?,?,?)",
                (username, hashed_password, encrypted_secret, now),
            )
            return cur.lastrowid

    def update_password_hash(self, user_id, encoded):
        with self.connection() as db:
            db.execute("UPDATE users SET password_hash=? WHERE id=?", (encoded, user_id))

    def is_limited(self, key, *, now=None):
        now = int(time.time() if now is None else now)
        with self.connection() as db:
            row = db.execute("SELECT blocked_until FROM rate_limits WHERE rate_key=?", (key,)).fetchone()
            return bool(row and row["blocked_until"] > now)

    def record_failed_attempt(self, key, *, limit=12, window=900, block=900, now=None):
        now = int(time.time() if now is None else now)
        with self.connection() as db:
            row = db.execute("SELECT * FROM rate_limits WHERE rate_key=?", (key,)).fetchone()
            if row is None or now - row["window_start"] >= window:
                db.execute("INSERT OR REPLACE INTO rate_limits(rate_key,window_start,failures,blocked_until) VALUES(?,?,1,0)",
                           (key, now))
                return
            count = int(row["failures"]) + 1
            until = (now + block) if count >= limit else row["blocked_until"]
            db.execute("UPDATE rate_limits SET failures=?,blocked_until=? WHERE rate_key=?", (count, until, key))

    def clear_failed_attempts(self, key):
        with self.connection() as db:
            db.execute("DELETE FROM rate_limits WHERE rate_key=?", (key,))

    def password_failure(self, user_id, *, now=None):
        now = int(time.time() if now is None else now)
        with self.connection() as db:
            db.execute("""UPDATE users SET failed_password=failed_password+1,
                password_locked_until=CASE WHEN failed_password+1>=6 THEN ? ELSE password_locked_until END
                WHERE id=?""", (now + 900, user_id))

    def password_success(self, user_id):
        with self.connection() as db:
            db.execute("UPDATE users SET failed_password=0,password_locked_until=0 WHERE id=?", (user_id,))

    def otp_failure(self, user_id, *, now=None):
        now = int(time.time() if now is None else now)
        with self.connection() as db:
            db.execute("""UPDATE users SET failed_otp=failed_otp+1,
                otp_locked_until=CASE WHEN failed_otp+1>=6 THEN ? ELSE otp_locked_until END
                WHERE id=?""", (now + 900, user_id))

    def consume_otp(self, user_id, counter, *, activate=False, now=None):
        now = int(time.time() if now is None else now)
        with self.connection() as db:
            # UPDATE atomico impedisce il riutilizzo concorrente di un OTP.
            cur = db.execute("""UPDATE users SET last_otp_counter=?, active=CASE WHEN ? THEN 1 ELSE active END,
                failed_otp=0,otp_locked_until=0
                WHERE id=? AND last_otp_counter<? AND otp_locked_until<=? AND active=?""",
                (counter, 1 if activate else 0, user_id, counter, now, 0 if activate else 1))
            return cur.rowcount == 1

    def create_session(self, user_id, *, now=None):
        now = int(time.time() if now is None else now)
        token = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(token.encode("ascii")).hexdigest()
        with self.connection() as db:
            db.execute("INSERT INTO sessions(token_hash,user_id,created_at,last_seen,expires_at) VALUES (?,?,?,?,?)",
                       (token_hash, user_id, now, now, now + SESSION_MAX_SECONDS))
        return token

    def current_user(self, token, *, now=None):
        if not isinstance(token, str) or len(token) < 40 or len(token) > 200:
            return None
        now = int(time.time() if now is None else now)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        with self.connection() as db:
            row = db.execute("""SELECT s.last_seen,s.expires_at,u.id,u.username,u.active FROM sessions AS s
                JOIN users AS u ON u.id=s.user_id WHERE s.token_hash=?""", (token_hash,)).fetchone()
            if row is None:
                return None
            if row["active"] != 1 or row["expires_at"] <= now or now - row["last_seen"] > SESSION_IDLE_SECONDS:
                db.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash,))
                return None
            db.execute("UPDATE sessions SET last_seen=? WHERE token_hash=?", (now, token_hash))
            return {"id": row["id"], "username": row["username"]}

    def revoke_session(self, token):
        if not token or not isinstance(token, str):
            return
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        with self.connection() as db:
            db.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash,))

    def remove_expired(self, *, now=None):
        now = int(time.time() if now is None else now)
        with self.connection() as db:
            db.execute("DELETE FROM sessions WHERE expires_at<=? OR last_seen<?", (now, now - SESSION_IDLE_SECONDS))
            db.execute("DELETE FROM users WHERE active=0 AND created_at<?", (now - SIGNUP_CHALLENGE_SECONDS,))
            db.execute("DELETE FROM rate_limits WHERE window_start<? AND blocked_until<=?", (now-86400, now))
