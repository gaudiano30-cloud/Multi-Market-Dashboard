"""End-to-end test of the window, driven by code on Qt's 'offscreen' platform (no screen needed).

Set SCREENSHOT_DIR=some/folder to also save a PNG of every page.
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pyotp  # noqa: E402
import pytest  # noqa: E402

QtWidgets = pytest.importorskip("PySide6.QtWidgets")
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from secureapp import config, ui  # noqa: E402
from secureapp.auth import GENERIC_LOGIN_ERROR, AuthService  # noqa: E402

PW = "correct horse battery staple"


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance() or QApplication([])
    ui._apply_light_appearance(application)
    return application


def pump(ms: int = 20) -> None:
    QTest.qWait(ms)  # let queued signals/timers run


def shot(window, name: str) -> None:
    folder = os.environ.get("SCREENSHOT_DIR")
    if folder:
        os.makedirs(folder, exist_ok=True)
        window.grab().save(os.path.join(folder, f"{name}.png"))


def test_full_flow(app, store, clock):
    auth = AuthService(store, clock=clock.wall, monotonic=clock.mono)
    win = ui.MainWindow(auth)
    win.show()
    pump()

    # 1. first launch: the window opens directly on account creation
    assert win.stack.currentWidget() is win.setup_page
    assert not win.logout_action.isEnabled()
    shot(win, "1_setup")
    setup = win.setup_page
    setup.username.setText("andrea")
    setup.password.setText(PW)
    setup.confirm.setText("something else")
    setup.button.click()
    assert "do not match" in setup.message.text()
    setup.confirm.setText(PW)
    setup.button.click()

    # 2. two-factor setup with QR code
    assert win.stack.currentWidget() is win.enroll_page
    assert not win.enroll_page.qr.pixmap().isNull()
    secret = win.pending.totp_secret
    assert secret.replace(" ", "")[:4] in win.enroll_page.secret.text()
    shot(win, "2_enroll")
    valid = {pyotp.TOTP(secret).at(clock.now + 30 * k) for k in (-1, 0, 1)}
    wrong = next(c for c in ("000000", "111111", "222222") if c not in valid)
    win.enroll_page.code.setText(wrong)  # 6 digits: submitted automatically
    pump()
    assert win.stack.currentWidget() is win.enroll_page
    assert "Invalid code" in win.enroll_page.message.text()
    win.enroll_page.code.setText(pyotp.TOTP(secret).at(clock.now))
    pump()

    # 3. recovery codes, shown once
    assert win.stack.currentWidget() is win.codes_page
    codes = win.codes_page.codes.toPlainText().splitlines()
    assert len(codes) == config.RECOVERY_CODE_COUNT
    shot(win, "3_recovery_codes")
    assert not win.codes_page.button.isEnabled()
    win.codes_page.ack.setChecked(True)
    win.codes_page.button.click()

    # 4. main window: white and empty
    assert win.stack.currentWidget() is win.home_page
    assert win.logout_action.isEnabled()
    assert win.home_page.findChildren(QWidget) == []
    pump()
    image = win.home_page.grab().toImage()
    assert image.pixelColor(image.width() // 2, image.height() // 2).name() == "#ffffff"
    assert win.codes_page.codes.toPlainText() == ""  # codes wiped once the page is left
    shot(win, "4_home")

    # 5. log out (Account > Log Out, ⌘L)
    win.logout_action.trigger()
    assert win.stack.currentWidget() is win.login_page
    assert "signed out" in win.login_page.message.text()

    # 6. level 1: wrong password, then right password
    login = win.login_page
    login.username.setText("andrea")
    login.password.setText("not the right passphrase")
    login.button.click()
    assert login.message.text() == GENERIC_LOGIN_ERROR and login.password.text() == ""
    clock.advance(31)
    login.password.setText(PW)
    shot(win, "5_login")
    login.button.click()
    assert win.stack.currentWidget() is win.otp_page

    # 7. level 2: wrong code, then right code
    win.otp_page.code.setText(next(c for c in ("123456", "654321") if c not in
                                   {pyotp.TOTP(secret).at(clock.now + 30 * k) for k in (-1, 0, 1)}))
    pump()
    assert "Invalid code" in win.otp_page.message.text()
    shot(win, "6_otp")
    win.otp_page.code.setText(pyotp.TOTP(secret).at(clock.now))
    pump()
    assert win.stack.currentWidget() is win.home_page

    # 8. inactivity: the session expires and the window goes back to sign-in
    clock.advance(config.SESSION_IDLE_TIMEOUT + 1)
    win._check_session()
    assert win.stack.currentWidget() is win.login_page
    assert "expired" in win.login_page.message.text()
    shot(win, "7_expired")

    # 9. recovery code instead of the authenticator
    login.username.setText("andrea")
    login.password.setText(PW)
    login.button.click()
    win.otp_page.toggle.click()
    win.otp_page.recovery.setText(codes[0])
    win.otp_page.button.click()
    assert win.stack.currentWidget() is win.home_page
    win.close()
