"""SQLite storage for users, recovery codes and the audit log.

Every query uses ? placeholders: values are never pasted into SQL text, so SQL
injection is not possible. The database file is readable by its owner only (0600).
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    username         TEXT    NOT NULL UNIQUE,
    role             TEXT    NOT NULL,
    password_hash    TEXT    NOT NULL,            -- Argon2id, contains its own salt
    kdf_salt         BLOB    NOT NULL,            -- salt of the key that encrypts the TOTP secret
    totp_secret_enc  BLOB,                        -- AES-256-GCM; NULL until 2FA is set up
    totp_last_step   INTEGER NOT NULL DEFAULT 0,  -- last accepted TOTP time-step (anti-replay)
    failed_attempts  INTEGER NOT NULL DEFAULT 0,
    locked_until     REAL    NOT NULL DEFAULT 0,  -- Unix time
    created_at       TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    last_login_at    TEXT
);
CREATE TABLE IF NOT EXISTS recovery_codes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    code_hash  TEXT    NOT NULL,
    used_at    TEXT
);
CREATE INDEX IF NOT EXISTS idx_recovery_codes_user ON recovery_codes(user_id);
CREATE TABLE IF NOT EXISTS audit_log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    at        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    username  TEXT,
    event     TEXT NOT NULL,
    detail    TEXT
);
"""


class Store:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not self.path.exists():  # create the file private *before* writing anything
            os.close(os.open(self.path, os.O_CREAT | os.O_WRONLY, 0o600))
        os.chmod(self.path, 0o600)
        self._db = sqlite3.connect(self.path)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys = ON")
        self._db.executescript(SCHEMA)

    def close(self) -> None:
        self._db.close()

    # --- users -------------------------------------------------------------------
    def count_users(self) -> int:
        return self._db.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    def user_by_name(self, username: str) -> sqlite3.Row | None:
        return self._db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

    def user_by_id(self, user_id: int) -> sqlite3.Row | None:
        return self._db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    def add_user(self, username: str, role: str, password_hash: str, kdf_salt: bytes) -> int:
        """Raise sqlite3.IntegrityError if the username already exists."""
        with self._db:
            cur = self._db.execute(
                "INSERT INTO users (username, role, password_hash, kdf_salt) VALUES (?, ?, ?, ?)",
                (username, role, password_hash, kdf_salt),
            )
        return int(cur.lastrowid)

    def set_password_hash(self, user_id: int, password_hash: str) -> None:
        with self._db:
            self._db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))

    def set_password(self, user_id: int, password_hash: str, kdf_salt: bytes, totp_secret_enc: bytes | None) -> None:
        with self._db:
            self._db.execute(
                "UPDATE users SET password_hash = ?, kdf_salt = ?, totp_secret_enc = ? WHERE id = ?",
                (password_hash, kdf_salt, totp_secret_enc, user_id),
            )

    # --- second factor --------------------------------------------------------------
    def enable_totp(self, user_id: int, secret_enc: bytes, step: int, recovery_hashes: list[str]) -> None:
        """Save the encrypted TOTP secret and replace the recovery codes, atomically."""
        with self._db:
            self._db.execute(
                "UPDATE users SET totp_secret_enc = ?, totp_last_step = ? WHERE id = ?",
                (secret_enc, step, user_id),
            )
            self._db.execute("DELETE FROM recovery_codes WHERE user_id = ?", (user_id,))
            self._db.executemany(
                "INSERT INTO recovery_codes (user_id, code_hash) VALUES (?, ?)",
                [(user_id, h) for h in recovery_hashes],
            )

    def advance_totp_step(self, user_id: int, step: int) -> bool:
        """Accept `step` only if it is newer than the last one used: a code works once."""
        with self._db:
            cur = self._db.execute(
                "UPDATE users SET totp_last_step = ? WHERE id = ? AND totp_last_step < ?",
                (step, user_id, step),
            )
        return cur.rowcount == 1

    def consume_recovery_code(self, user_id: int, code_hash: str) -> bool:
        with self._db:
            cur = self._db.execute(
                "UPDATE recovery_codes SET used_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') "
                "WHERE id = (SELECT id FROM recovery_codes "
                "            WHERE user_id = ? AND code_hash = ? AND used_at IS NULL LIMIT 1)",
                (user_id, code_hash),
            )
        return cur.rowcount == 1

    def unused_recovery_codes(self, user_id: int) -> int:
        return self._db.execute(
            "SELECT COUNT(*) FROM recovery_codes WHERE user_id = ? AND used_at IS NULL", (user_id,)
        ).fetchone()[0]

    # --- brute-force protection ---------------------------------------------------------
    def register_failure(self, user_id: int, now: float, max_attempts: int, lockout_seconds: float) -> sqlite3.Row:
        """Count a failed attempt; after `max_attempts` in a row, lock the account."""
        with self._db:
            self._db.execute("UPDATE users SET failed_attempts = failed_attempts + 1 WHERE id = ?", (user_id,))
            self._db.execute(
                "UPDATE users SET locked_until = ?, failed_attempts = 0 WHERE id = ? AND failed_attempts >= ?",
                (now + lockout_seconds, user_id, max_attempts),
            )
        return self.user_by_id(user_id)

    def mark_login(self, user_id: int) -> None:
        with self._db:
            self._db.execute(
                "UPDATE users SET failed_attempts = 0, locked_until = 0, "
                "last_login_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
                (user_id,),
            )

    # --- audit log (never contains passwords, codes or secrets) ---------------------------
    def audit(self, event: str, username: str | None = None, detail: str | None = None) -> None:
        with self._db:
            self._db.execute(
                "INSERT INTO audit_log (username, event, detail) VALUES (?, ?, ?)", (username, event, detail)
            )

    def audit_events(self, limit: int = 100) -> list[sqlite3.Row]:
        return self._db.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
