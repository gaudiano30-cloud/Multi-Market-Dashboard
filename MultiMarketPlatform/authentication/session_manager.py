"""Gestione indipendente delle sessioni server-side revocabili.

Il repository salva soltanto l'hash del token (SHA-256); il cookie HTTP contiene
un token casuale firmato dalla sessione Flask, non le credenziali dell'utente.
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
