"""Rules for usernames and passwords (NIST SP 800-63B-4, §3.1.1.2).

NIST asks for length, a blocklist of common/context-specific passwords and *no*
composition rules ("one uppercase, one symbol...") and no periodic expiry.
"""
from __future__ import annotations

import re
import unicodedata

from . import config

_USERNAME_RE = re.compile(r"[a-z0-9][a-z0-9._-]{2,31}")

# Passwords people actually pick. A password is rejected when, after removing leading /
# trailing digits and symbols and undoing common "leet" substitutions, what is left is one
# of these words ("Password2024!", "P@ssw0rd", "Qwerty123456" are all rejected).
# For a production system you can add a large breached-password list here.
_COMMON_WORDS = frozenset({
    "password", "passwort", "qwerty", "qwertyuiop", "azerty", "asdfghjkl", "zxcvbnm",
    "admin", "administrator", "welcome", "benvenuto", "letmein", "iloveyou", "ciao",
    "abc", "abcdef", "abcdefgh", "monkey", "dragon", "football", "calcio", "juventus",
    "milan", "inter", "baseball", "sunshine", "princess", "master", "secret", "segreto",
    "changeme", "trustno", "superman", "batman", "login", "user", "guest", "test",
    "default", "root", "qazwsx", "starwars", "whatever", "freedom", "shadow",
})
_LEET = str.maketrans({"@": "a", "4": "a", "0": "o", "1": "i", "3": "e", "5": "s", "$": "s", "7": "t"})
_SEQUENCES = ("0123456789" * 4, "abcdefghijklmnopqrstuvwxyz" * 2, "qwertyuiopasdfghjklzxcvbnm" * 2)


def normalize_username(username: str) -> str:
    """Usernames are case-insensitive: 'Andrea' and 'andrea' are the same account."""
    return unicodedata.normalize("NFKC", username or "").strip().casefold()


def username_problem(username: str) -> str | None:
    if not _USERNAME_RE.fullmatch(username):
        return "Username: 3-32 characters (letters, digits, dot, dash or underscore)."
    return None


def password_problems(password: str, username: str = "") -> list[str]:
    """Return the reasons why `password` is not acceptable (an empty list means OK)."""
    pw = unicodedata.normalize("NFKC", password or "")
    lowered = pw.casefold()
    problems: list[str] = []

    if len(pw) < config.PASSWORD_MIN_LENGTH:
        problems.append(f"Use at least {config.PASSWORD_MIN_LENGTH} characters.")
    if len(pw) > config.PASSWORD_MAX_LENGTH:
        problems.append(f"Use at most {config.PASSWORD_MAX_LENGTH} characters.")
    if username and username.casefold() in lowered:
        problems.append("The password must not contain the username.")
    if config.APP_NAME.casefold() in lowered:
        problems.append("The password must not contain the application name.")

    core = re.sub(r"^[\W\d_]+|[\W\d_]+$", "", lowered).translate(_LEET)
    if (
        core in _COMMON_WORDS
        or len(set(lowered)) < 4  # "aaaaaaaaaaaa", "abababababab"
        or any(lowered in seq or lowered in seq[::-1] for seq in _SEQUENCES)  # "123456789012"
    ):
        problems.append("This password is too common or easy to guess: try a passphrase of a few words.")
    return problems
