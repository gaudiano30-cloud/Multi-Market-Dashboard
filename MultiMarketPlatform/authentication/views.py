"""Schermate di ingresso, registrazione e doppia verifica (Flask Blueprint)."""
import base64
import hmac
import io
import secrets
import time
from pathlib import Path

import qrcode
from flask import (Blueprint, abort, current_app, redirect, render_template,
                   request, session, url_for, send_from_directory)

from .auth_service import AuthError
from .settings import SIGNIN_CHALLENGE_SECONDS, SIGNUP_CHALLENGE_SECONDS

auth_bp = Blueprint("auth", __name__, url_prefix="/auth", template_folder="templates", static_folder="static")


def service():
    return current_app.extensions["mfe_auth_service"]


def _csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


def _require_csrf():
    token = request.form.get("csrf_token", "")
    if not token or not hmac.compare_digest(str(token), str(session.get("csrf", ""))):
        abort(400, "Token CSRF non valido. Ricarica la pagina e riprova.")


@auth_bp.app_context_processor
def auth_template_context():
    return {"csrf_token": _csrf_token}


def _rate_key(category):
    # Non usare X-Forwarded-For non attendibile da Internet.
    ip = request.remote_addr or "unknown"
    return service().client_rate_key(category, ip)


def _has_access():
    return service().current_user(session.get("auth_token")) is not None


def _set_authenticated(token):
    session.clear()
    session["auth_token"] = token


def _stage_user(key, expiry_key, max_seconds):
    uid = session.get(key)
    expires = session.get(expiry_key)
    if not isinstance(uid, int) or not isinstance(expires, int) or time.time() >= expires:
        return None
    return uid


@auth_bp.route("/", methods=["GET"])
def welcome():
    if _has_access():
        return redirect("/")
    return render_template("welcome.html", page_title="Benvenuto")


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if _has_access():
        return redirect("/")
    error = None
    if request.method == "POST":
        _require_csrf()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("password_confirm", "")
        if password != confirm:
            error = "Le password non coincidono."
        else:
            try:
                uid = service().register(username, password, rate_key=_rate_key("signup"))
            except AuthError as exc:
                error = str(exc)
            else:
                session.clear()
                session["setup_user"] = uid
                session["setup_expires"] = int(time.time()) + SIGNUP_CHALLENGE_SECONDS
                return redirect(url_for("auth.setup_otp"))
    return render_template("signup.html", page_title="Sign up", error=error)


@auth_bp.route("/setup-otp", methods=["GET", "POST"])
def setup_otp():
    if _has_access():
        return redirect("/")
    uid = _stage_user("setup_user", "setup_expires", SIGNUP_CHALLENGE_SECONDS)
    if uid is None:
        session.clear()
        return redirect(url_for("auth.signup"))
    try:
        secret, uri = service().setup_details(uid)
    except AuthError:
        session.clear()
        return redirect(url_for("auth.signup"))
    error = None
    if request.method == "POST":
        _require_csrf()
        code = request.form.get("otp", "").strip()
        try:
            token = service().verify_second_factor(
                uid, code, activate=True, rate_key=_rate_key("otp"))
        except AuthError as exc:
            error = str(exc)
        else:
            _set_authenticated(token)
            return redirect("/")
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(uri)
    qr.make(fit=True)
    buffer = io.BytesIO()
    qr.make_image(fill_color="#001a3e", back_color="white").save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return render_template("setup_otp.html", page_title="Configura OTP", error=error,
                           otp_secret=secret, qr_data=f"data:image/png;base64,{encoded}")


@auth_bp.route("/signin", methods=["GET", "POST"])
def signin():
    if _has_access():
        return redirect("/")
    error = None
    if request.method == "POST":
        _require_csrf()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        try:
            user_id = service().verify_first_factor(username, password, rate_key=_rate_key("signin"))
        except AuthError as exc:
            error = str(exc)
        else:
            # La password non dà accesso alla dashboard: soltanto un challenge OTP.
            session.clear()
            session["pending_user"] = user_id
            session["pending_expires"] = int(time.time()) + SIGNIN_CHALLENGE_SECONDS
            session["pending_attempts"] = 0
            return redirect(url_for("auth.otp"))
    return render_template("signin.html", page_title="Sign in", error=error)


@auth_bp.route("/otp", methods=["GET", "POST"])
def otp():
    if _has_access():
        return redirect("/")
    uid = _stage_user("pending_user", "pending_expires", SIGNIN_CHALLENGE_SECONDS)
    if uid is None or session.get("pending_attempts", 0) >= 6:
        session.clear()
        return redirect(url_for("auth.signin"))
    error = None
    if request.method == "POST":
        _require_csrf()
        code = request.form.get("otp", "").strip()
        try:
            token = service().verify_second_factor(
                uid, code, activate=False, rate_key=_rate_key("otp"))
        except AuthError as exc:
            session["pending_attempts"] = session.get("pending_attempts", 0) + 1
            error = str(exc)
        else:
            _set_authenticated(token)
            return redirect("/")
    return render_template("otp.html", page_title="Verifica OTP", error=error)


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    if request.method == "POST":
        _require_csrf()
        service().logout(session.get("auth_token"))
        session.clear()
        return redirect(url_for("auth.welcome"))
    if not _has_access():
        session.clear()
        return redirect(url_for("auth.welcome"))
    return render_template("logout.html", page_title="Esci")


@auth_bp.route("/brand-logo", methods=["GET"])
def brand_logo():
    """L'unico asset Dash pubblico: logo della pagina di accesso."""
    from .settings import ROOT
    return send_from_directory(ROOT / "assets", "MFEimage.png")
