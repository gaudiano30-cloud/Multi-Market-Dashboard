"""
Session Management Module.

This module manages revocable server-side authentication
sessions, independently of the user interface.

Its main responsibilities include:
    - Issuing new authenticated user sessions.
    - Identifying users through their session tokens.
    - Revoking existing sessions during logout.

Session persistence and token management are delegated
to the repository.

For security purposes, the repository stores only the
SHA-256 hash of each session token, while the signed
Flask session cookie carries the original random token
without containing the user's authentication credentials.

The SessionManager class provides a centralized and
reusable interface for session management to the
authentication service.
"""


class SessionManager:
    def __init__(self, repository):
        self.repository = repository

    def issue(self, user_id, *, now=None):
        return self.repository.create_session(user_id, now=now)

    def identify(self, token, *, now=None):
        return self.repository.current_user(token, now=now)

    def revoke(self, token):
        self.repository.revoke_session(token)
