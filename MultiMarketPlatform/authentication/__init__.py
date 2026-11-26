"""Questo file è diventato il punto d'ingresso del sistema di sicurezza.
Questo file è particolarmente interessante perché rappresenta il collegamento tra la dashboard finanziaria e il sistema di autenticazione.
authentication aggiunga un controllo degli accessi soltanto se il package è presente.
authentication/__init__.py non avvia Dash e non crea una nuova dashboard. Configura soltanto il sistema di sicurezza sul server che Dash ha già creato.


Protezione 2FA facoltativa per una Dash gia creata da main.py.

L'autenticazione si collega all'oggetto Dash ricevuto: non crea una nuova app.
L'assenza del package e gestita da main.py; errori di sicurezza, invece,
impediscono l'avvio (fail closed).
"""

import os  # Il modulo os fa parte della libreria standard di Python e permette di interagire con il sistema operativo.


def protect_dash(app):
    """Sto definendo una funzione chiamata protect_dash che riceve un oggetto chiamato app. Nel nostro caso app è la dashboard creata da main.py."""

    """Collega Sign in, Sign up, OTP, sessioni e access control a `app`.

    Deve essere chiamata dopo `Dash(...)` e prima di servire richieste HTTP.
    Restituisce lo stesso oggetto ricevuto, senza sostituire app.layout o callback.
    """
    """"Python esegue gli import quando la funzione viene chiamata, anziché durante la semplice importazione del package.

    È utile per mantenere il punto di ingresso leggero e isolare l'inizializzazione della sicurezza.
    """
    from flask import Response, redirect, request, session

    # il punto . significa: Cerca il modulo settings all'interno dello stesso package in cui ci troviamo.
    from .settings import DB_PATH, load_secret_key, secret_cipher
    from .auth_service import AuthService
    from .storage import IdentityStore
    from .views import auth_bp

    flask_server = app.server
    if "mfe_auth_service" in flask_server.extensions:
        return app  # evita di registrare due volte Blueprint e filtri
    # Se il sistema di autenticazione è già stato collegato a Flask, non configurarlo una seconda volta.

    key = load_secret_key()
    store = IdentityStore(DB_PATH)
    security = AuthService(store, secret_cipher(key), key)
    # Qui creiamo tre elementi.
    # key: una chiave segreta utilizzata dall'applicazione per alcune operazioni di sicurezza.
    # store: un oggetto che permette di comunicare con il database degli utenti.
    # security: un oggetto che sa gestire registrazione, verifica delle password, OTP e sessioni.

    # Il Flask server e stato creato da Dash, non dal package authentication.
    flask_server.secret_key = key
    flask_server.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("MFE_HTTPS", "0") == "1",
        SESSION_COOKIE_NAME="mfe_session",
        MAX_CONTENT_LENGTH=32 * 1024,
    )
    flask_server.extensions["mfe_auth_service"] = security
    flask_server.register_blueprint(auth_bp)

    @flask_server.before_request
    def require_2fa_for_dashboard():
        # Sono pubbliche solo le pagine e le risorse di autenticazione.
        if request.path == "/auth":
            return redirect("/auth/")
        if request.path.startswith("/auth/"):
            return None

        # Protegge anche /_dash-layout, /_dash-update-component e gli assets.
        # La password da sola non basta: current_user richiede una sessione
        # creata dopo la verifica OTP.
        if security.current_user(session.get("auth_token")) is not None:
            return None
        if request.path == "/" and request.method in ("GET", "HEAD"):
            return redirect("/auth/")
        return Response("Accesso negato: completa username/password e OTP.", status=401)

    @flask_server.after_request
    def secure_headers(response):
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    return app
