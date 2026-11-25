"""Factory del servizio Dash protetto.

L'applicazione principale resta in main.py. Tutta l'autenticazione e la
protezione degli endpoint sono qui, indipendenti da mercati e analytics.
"""
import os

from .settings import DB_PATH, INSTANCE, ROOT, load_secret_key, secret_cipher


def create_authenticated_dash(name: str, **dash_kwargs):
    """Restituisce un'istanza Dash con route Flask e API protette da 2FA."""
    from dash import Dash
    from flask import Flask, Response, redirect, request, session
    from .auth_service import AuthService
    from .storage import IdentityStore
    from .views import auth_bp

    key = load_secret_key()
    store = IdentityStore(DB_PATH)
    security = AuthService(store, secret_cipher(key), key)

    flask_server = Flask(name, static_folder=None, instance_path=str(INSTANCE))
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
        # SOLO /auth e /auth/* sono pubblici. Il logo pubblico vive in /auth/brand-logo.
        if request.path == "/auth":
            return redirect("/auth/")
        if request.path.startswith("/auth/"):
            return None
        # IMPORTANTISSIMO: protegge anche le API Dash (layout, callbacks, assets).
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

    dash_kwargs.setdefault("assets_folder", str(ROOT / "assets"))
    dash_kwargs.setdefault("suppress_callback_exceptions", True)
    return Dash(name, server=flask_server, **dash_kwargs)
