"""Integration test HTTP, eseguito quando Dash/Flask/qrcode sono installati."""
import time

import pytest

flask = pytest.importorskip("flask")
dash = pytest.importorskip("dash")
pytest.importorskip("qrcode")

from authentication import otp_manager
import authentication as auth_package


def test_signup_otp_protects_dash_and_logout(tmp_path, monkeypatch):
    # Usa un database e una chiave di prova in una directory temporanea.
    monkeypatch.setattr(auth_package, "INSTANCE", tmp_path)
    monkeypatch.setattr(auth_package, "DB_PATH", tmp_path / "testing.sqlite3")
    monkeypatch.setattr(auth_package, "load_secret_key", lambda: "testing-secret-key-is-long-and-isolated-2026")

    app = auth_package.create_authenticated_dash("test_mfe", title="Test 2FA")
    app.layout = dash.html.Div("Dashboard di prova")
    client = app.server.test_client()
    assert client.get("/").status_code == 302
    assert client.get("/_dash-layout").status_code == 401
    assert client.post("/_dash-update-component", json={}).status_code == 401
    assert client.get("/auth/").status_code == 200
    assert client.get("/auth/signup").status_code == 200
    assert client.get("/auth/brand-logo").status_code == 200
    assert client.get("/assets/MFEimage.png").status_code == 401

    with client.session_transaction() as sess:
        csrf = sess["csrf"]
    result = client.post("/auth/signup", data={
        "csrf_token": csrf, "username": "test_user",
        "password": "very-secure-example-2026", "password_confirm": "very-secure-example-2026"
    })
    assert result.status_code == 302
    assert "/auth/setup-otp" in result.headers["Location"]
    assert client.get("/_dash-layout").status_code == 401  # Password non basta.

    service = app.server.extensions["mfe_auth_service"]
    with client.session_transaction() as sess:
        uid = sess["setup_user"]
    secret, _ = service.setup_details(uid)
    assert client.get("/auth/setup-otp").status_code == 200
    with client.session_transaction() as sess:
        csrf = sess["csrf"]
    code = otp_manager.code_at(secret, int(time.time() // 30))
    done = client.post("/auth/setup-otp", data={"csrf_token": csrf, "otp": code})
    assert done.status_code == 302
    assert client.get("/_dash-layout").status_code == 200
    assert client.get("/").status_code == 200

    assert client.get("/auth/logout").status_code == 200
    with client.session_transaction() as sess:
        csrf = sess["csrf"]
    assert client.post("/auth/logout", data={"csrf_token": csrf}).status_code == 302
    assert client.get("/_dash-layout").status_code == 401
