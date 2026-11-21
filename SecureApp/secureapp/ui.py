"""PySide6 user interface: one window holding a stack of pages.

    first launch    SetupPage ─► EnrollPage ─► RecoveryCodesPage ─► HomePage
    every launch    LoginPage ─► OtpPage ───────────────────────► HomePage

The UI never decides who is signed in: it only shows what AuthService returns.
"""
from __future__ import annotations

import logging
import sys
from contextlib import contextmanager
from pathlib import Path

import qrcode
from PySide6.QtCore import QEvent, QObject, QRegularExpression, Qt, QTimer, Signal
from PySide6.QtGui import (QAction, QColor, QFont, QGuiApplication, QImage, QKeySequence, QPalette, QPixmap,
                           QRegularExpressionValidator)
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
                               QMessageBox, QPlainTextEdit, QPushButton, QStackedWidget, QVBoxLayout, QWidget)

from . import config
from .auth import AuthError, AuthService, PendingEnrollment, PendingLogin, RestartRequired, Session
from .storage import Store

log = logging.getLogger(__name__)

QR_SIZE = 200

STYLE = """
QWidget#page { background: #ffffff; }
QFrame#card { background: #ffffff; border: 1px solid #e5e5ea; border-radius: 14px; }
QLabel { background: transparent; }
QLabel#title { font-size: 22px; font-weight: 600; color: #1d1d1f; }
QLabel#subtitle, QLabel#hint { color: #6e6e73; }
QLabel#error { color: #d70015; }
QLabel#info { color: #0a5bb5; }
QLabel#secret { color: #3a3a3c; font-family: Menlo, "DejaVu Sans Mono", monospace; }
QLineEdit { border: 1px solid #d2d2d7; border-radius: 8px; padding: 6px 10px;
            background: #ffffff; color: #1d1d1f; selection-background-color: #b3d7ff; }
QLineEdit:focus { border: 1px solid #0071e3; }
QPlainTextEdit#codes { border: 1px solid #d2d2d7; border-radius: 8px; padding: 8px; background: #f5f5f7;
                       color: #1d1d1f; font-family: Menlo, "DejaVu Sans Mono", monospace; font-size: 15px; }
QPushButton#primary { background: #0071e3; color: #ffffff; border: none; border-radius: 8px;
                      padding: 9px 16px; font-weight: 600; }
QPushButton#primary:hover { background: #0077ed; }
QPushButton#primary:pressed { background: #006edb; }
QPushButton#primary:disabled { background: #a8c9f0; }
QPushButton#link { background: transparent; color: #0066cc; border: none; padding: 4px; }
QPushButton#link:hover { color: #004f9e; }
"""


# ---------------------------------------------------------------------------------- helpers
def _label(text: str = "", name: str | None = None) -> QLabel:
    label = QLabel(text)
    if name:
        label.setObjectName(name)
    label.setWordWrap(True)
    return label


def _field(placeholder: str, secret: bool = False) -> QLineEdit:
    field = QLineEdit()
    field.setPlaceholderText(placeholder)
    field.setMinimumHeight(38)
    if secret:
        field.setEchoMode(QLineEdit.EchoMode.Password)  # Qt also disables copying from it
    return field


def _code_field() -> QLineEdit:
    field = QLineEdit()
    field.setMaxLength(6)
    field.setPlaceholderText("000000")
    field.setValidator(QRegularExpressionValidator(QRegularExpression(r"[0-9]{0,6}"), field))
    field.setAlignment(Qt.AlignmentFlag.AlignCenter)
    font = QFont(field.font())
    font.setPixelSize(26)
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 6)
    field.setFont(font)
    field.setMinimumHeight(54)
    return field


def _button(text: str, primary: bool = True) -> QPushButton:
    button = QPushButton(text)
    button.setObjectName("primary" if primary else "link")
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    if primary:
        button.setMinimumHeight(40)
    return button


def qr_pixmap(data: str, size: int, ratio: float = 1.0) -> QPixmap:
    """Render `data` as a QR code with whole-pixel modules (sharp on Retina screens)."""
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    n = len(matrix)
    image = QImage(n, n, QImage.Format.Format_RGB32)
    image.fill(QColor("white"))
    black = QColor("black").rgb()
    for y, row in enumerate(matrix):
        for x, dark in enumerate(row):
            if dark:
                image.setPixel(x, y, black)
    target = max(n, int(size * ratio) // n * n)
    pixmap = QPixmap.fromImage(image.scaled(target, target, Qt.AspectRatioMode.KeepAspectRatio,
                                            Qt.TransformationMode.FastTransformation))
    pixmap.setDevicePixelRatio(ratio)
    return pixmap


@contextmanager
def busy():
    """Wait cursor while Argon2id works (a fraction of a second, on purpose)."""
    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        yield
    finally:
        QApplication.restoreOverrideCursor()


# ------------------------------------------------------------------------------------ pages
class Page(QWidget):
    """White page with a centred card: title, subtitle, fields and a message line."""

    def __init__(self, title: str, subtitle: str = "", width: int = 400) -> None:
        super().__init__()
        self.setObjectName("page")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.card = QFrame()
        self.card.setObjectName("card")
        self.card.setFixedWidth(width)
        self.body = QVBoxLayout(self.card)
        self.body.setContentsMargins(32, 30, 32, 26)
        self.body.setSpacing(10)
        self.body.addWidget(_label(title, "title"))
        if subtitle:
            self.body.addWidget(_label(subtitle, "subtitle"))
        self.body.addSpacing(6)
        self.message = _label("", "error")
        self.message.hide()
        # Centre the card with stretches rather than alignment flags: this way Qt computes
        # its height from the real width, and wrapped text is never clipped.
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(self.card)
        row.addStretch(1)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.addStretch(1)
        outer.addLayout(row)
        outer.addStretch(1)
        self.first_field: QWidget | None = None

    def add(self, *widgets: QWidget) -> None:
        for widget in widgets:
            self.body.addWidget(widget)

    def show_message(self, text: str, kind: str = "error") -> None:
        self.message.setObjectName(kind)  # "error" (red) or "info" (blue)
        self.message.style().unpolish(self.message)
        self.message.style().polish(self.message)
        self.message.setText(text)
        self.message.setVisible(bool(text))

    def clear(self) -> None:
        """Forget everything typed or shown (called whenever the page is left)."""
        self.show_message("")
        for field in self.findChildren(QLineEdit):
            field.clear()


class SetupPage(Page):
    submitted = Signal(str, str)  # username, password

    def __init__(self) -> None:
        super().__init__("Create the administrator",
                         f"First launch of {config.APP_NAME}. This account will manage the platform; "
                         "next you will protect it with two-factor authentication.")
        self.username = _field("Username")
        self.password = _field("Password", secret=True)
        self.confirm = _field("Repeat password", secret=True)
        hint = _label(f"At least {config.PASSWORD_MIN_LENGTH} characters. "
                      "A passphrase of a few words is ideal.", "hint")
        self.button = _button("Create account")
        self.add(self.username, self.password, self.confirm, hint, self.message, self.button)
        self.first_field = self.username
        self.username.returnPressed.connect(self.password.setFocus)
        self.password.returnPressed.connect(self.confirm.setFocus)
        self.confirm.returnPressed.connect(self._submit)
        self.button.clicked.connect(self._submit)

    def _submit(self) -> None:
        if self.password.text() != self.confirm.text():
            self.confirm.clear()
            self.show_message("The two passwords do not match.")
            self.confirm.setFocus()
            return
        self.submitted.emit(self.username.text(), self.password.text())


class LoginPage(Page):
    submitted = Signal(str, str)

    def __init__(self) -> None:
        super().__init__("Sign in", f"Welcome to {config.APP_NAME}. Step 1 of 2: username and password.")
        self.username = _field("Username")
        self.password = _field("Password", secret=True)
        self.button = _button("Continue")
        self.add(self.username, self.password, self.message, self.button)
        self.first_field = self.username
        self.username.returnPressed.connect(self.password.setFocus)
        self.password.returnPressed.connect(self._submit)
        self.button.clicked.connect(self._submit)

    def _submit(self) -> None:
        self.submitted.emit(self.username.text(), self.password.text())


class OtpPage(Page):
    code_entered = Signal(str)
    recovery_entered = Signal(str)
    back = Signal()

    def __init__(self) -> None:
        super().__init__("Two-factor authentication",
                         "Step 2 of 2: enter the 6-digit code shown by your authenticator app.")
        self.code = _code_field()
        self.recovery = _field("Recovery code (XXXX-XXXX-XXXX-XXXX)")
        self.recovery.hide()
        self.button = _button("Verify")
        self.toggle = _button("Use a recovery code instead", primary=False)
        self.back_button = _button("← Back to sign in", primary=False)
        self.add(self.code, self.recovery, self.message, self.button, self.toggle, self.back_button)
        self.first_field = self.code
        self._recovery_mode = False
        self.code.textChanged.connect(self._maybe_auto_submit)
        self.code.returnPressed.connect(self._submit)
        self.recovery.returnPressed.connect(self._submit)
        self.button.clicked.connect(self._submit)
        self.toggle.clicked.connect(lambda: self.set_recovery_mode(not self._recovery_mode))
        self.back_button.clicked.connect(lambda: self.back.emit())

    def _maybe_auto_submit(self, text: str) -> None:
        if len(text) == 6:  # no need to press Verify once the 6th digit is typed
            QTimer.singleShot(0, self._submit)

    def _submit(self) -> None:
        if self._recovery_mode:
            self.recovery_entered.emit(self.recovery.text())
        elif self.code.text():
            self.code_entered.emit(self.code.text())

    def set_recovery_mode(self, on: bool) -> None:
        self._recovery_mode = on
        self.code.setVisible(not on)
        self.recovery.setVisible(on)
        self.toggle.setText("Use the authenticator app instead" if on else "Use a recovery code instead")
        self.show_message("")
        (self.recovery if on else self.code).setFocus()

    def clear(self) -> None:
        super().clear()
        self.set_recovery_mode(False)


class EnrollPage(Page):
    code_entered = Signal(str)
    cancelled = Signal()

    def __init__(self) -> None:
        super().__init__("Set up two-factor authentication",
                         "1. Open an authenticator app on your phone (Passwords on iPhone, "
                         "Google or Microsoft Authenticator…).\n2. Scan the QR code.\n"
                         "3. Type the 6-digit code it shows.", width=440)
        self.qr = QLabel()
        self.qr.setFixedSize(QR_SIZE, QR_SIZE)
        self.qr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        manual = _label("Can't scan it? Enter this key manually:", "hint")
        manual.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.secret = _label("", "secret")
        self.secret.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.secret.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.code = _code_field()
        self.button = _button("Activate")
        self.cancel = _button("Cancel", primary=False)
        self.body.addWidget(self.qr, 0, Qt.AlignmentFlag.AlignHCenter)
        self.add(manual, self.secret, self.code, self.message, self.button, self.cancel)
        self.first_field = self.code
        self.code.textChanged.connect(lambda t: len(t) == 6 and QTimer.singleShot(0, self._submit))
        self.code.returnPressed.connect(self._submit)
        self.button.clicked.connect(self._submit)
        self.cancel.clicked.connect(lambda: self.cancelled.emit())

    def set_secret(self, uri: str, secret: str) -> None:
        self.qr.setPixmap(qr_pixmap(uri, QR_SIZE, self.devicePixelRatioF()))
        self.secret.setText(" ".join(secret[i:i + 4] for i in range(0, len(secret), 4)))

    def _submit(self) -> None:
        if self.code.text():
            self.code_entered.emit(self.code.text())

    def clear(self) -> None:
        super().clear()
        self.qr.clear()
        self.secret.clear()


class RecoveryCodesPage(Page):
    finished = Signal()

    def __init__(self) -> None:
        super().__init__("Save your recovery codes",
                         "If you lose your phone, each code lets you sign in once instead of the 6-digit "
                         "code. They will not be shown again: keep them somewhere safe, such as your "
                         "password manager.", width=440)
        self.codes = QPlainTextEdit()
        self.codes.setObjectName("codes")
        self.codes.setReadOnly(True)
        self.codes.setFixedHeight(8 * 22 + 24)
        self.copy = _button("Copy to clipboard", primary=False)
        self.ack = QCheckBox("I have stored these codes in a safe place")
        self.button = _button("Continue")
        self.button.setEnabled(False)
        self.add(self.codes, self.copy, self.ack, self.message, self.button)
        self.ack.toggled.connect(self.button.setEnabled)
        self.copy.clicked.connect(self._copy)
        self.button.clicked.connect(lambda: self.finished.emit())

    def set_codes(self, codes: list[str]) -> None:
        self.codes.setPlainText("\n".join(codes))

    def _copy(self) -> None:
        QGuiApplication.clipboard().setText(self.codes.toPlainText())
        self.show_message("Copied. Paste them into your password manager.", "info")

    def clear(self) -> None:
        super().clear()
        self.codes.clear()
        self.ack.setChecked(False)


class HomePage(QWidget):
    """Main area of the application: intentionally white and empty for now.

    Build your content here. `self.session` is the signed-in user's Session (None when
    signed out) and `self.auth` the AuthService: put protected operations in AuthService
    (or another service) behind @requires("permission") and call them with self.session.
    """

    def __init__(self, auth: AuthService) -> None:
        super().__init__()
        self.setObjectName("page")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.auth = auth
        self.session: Session | None = None


# ------------------------------------------------------------------------------- main window
class MainWindow(QMainWindow):
    SESSION_CHECK_MS = 5_000
    ACTIVITY_EVENTS = {QEvent.Type.KeyPress, QEvent.Type.MouseButtonPress, QEvent.Type.Wheel}

    def __init__(self, auth: AuthService) -> None:
        super().__init__()
        self.auth = auth
        self.session: Session | None = None
        self.pending: PendingLogin | PendingEnrollment | None = None
        self.setWindowTitle(config.APP_NAME)
        self.resize(1100, 760)
        self.setMinimumSize(820, 700)

        self.setup_page = SetupPage()
        self.login_page = LoginPage()
        self.otp_page = OtpPage()
        self.enroll_page = EnrollPage()
        self.codes_page = RecoveryCodesPage()
        self.home_page = HomePage(auth)
        self.pages = (self.setup_page, self.login_page, self.otp_page, self.enroll_page, self.codes_page,
                      self.home_page)
        self.stack = QStackedWidget()
        for page in self.pages:
            self.stack.addWidget(page)
        self.setCentralWidget(self.stack)

        self.setup_page.submitted.connect(self._create_admin)
        self.enroll_page.code_entered.connect(self._confirm_enrollment)
        self.enroll_page.cancelled.connect(lambda: self._restart())
        self.codes_page.finished.connect(self._enter_home)
        self.login_page.submitted.connect(self._login)
        self.otp_page.code_entered.connect(lambda code: self._second_factor(self.auth.verify_otp, code))
        self.otp_page.recovery_entered.connect(
            lambda code: self._second_factor(self.auth.verify_recovery_code, code))
        self.otp_page.back.connect(lambda: self._restart())

        account_menu = self.menuBar().addMenu("&Account")  # on macOS: in the top menu bar
        self.logout_action = QAction("Log Out", self)
        self.logout_action.setShortcut(QKeySequence("Ctrl+L"))  # Qt maps Ctrl to ⌘ on macOS
        self.logout_action.triggered.connect(lambda: self.logout("You have been signed out."))
        account_menu.addAction(self.logout_action)

        self._session_timer = QTimer(self)
        self._session_timer.setInterval(self.SESSION_CHECK_MS)
        self._session_timer.timeout.connect(self._check_session)
        QApplication.instance().installEventFilter(self)  # any key/click counts as activity
        self._restart()

    # --- navigation ---------------------------------------------------------------------------
    def _show(self, page: QWidget) -> None:
        for other in self.pages:
            if other is not page and isinstance(other, Page):
                other.clear()
        self.stack.setCurrentWidget(page)
        self.logout_action.setEnabled(page is self.home_page)
        if isinstance(page, Page) and page.first_field is not None:
            QTimer.singleShot(0, page.first_field.setFocus)

    def _restart(self, message: str = "", kind: str = "info") -> None:
        """Back to step 1: account creation on first launch, otherwise the sign-in page."""
        self._close_pending()
        page = self.setup_page if self.auth.needs_setup() else self.login_page
        page.clear()
        self._show(page)
        page.show_message(message, kind)

    def _close_pending(self) -> None:
        if self.pending is not None:
            self.pending.close()
            self.pending = None

    # --- first launch -------------------------------------------------------------------------
    def _create_admin(self, username: str, password: str) -> None:
        try:
            with busy():
                pending = self.auth.create_admin(username, password)
        except AuthError as exc:
            self.setup_page.show_message(str(exc))
            return
        self._start_enrollment(pending)

    def _start_enrollment(self, pending: PendingEnrollment) -> None:
        self.pending = pending
        self.enroll_page.set_secret(pending.provisioning_uri, pending.totp_secret)
        self._show(self.enroll_page)

    def _confirm_enrollment(self, code: str) -> None:
        if self.pending is None or self.stack.currentWidget() is not self.enroll_page:
            return  # stray signal (e.g. Enter pressed right after the auto-submit)
        try:
            session, codes = self.auth.confirm_enrollment(self.pending, code)
        except RestartRequired as exc:
            self._restart(str(exc), "error")
            return
        except AuthError as exc:
            self.enroll_page.code.clear()
            self.enroll_page.show_message(str(exc))
            return
        self.pending = None
        self.session = session
        self.codes_page.set_codes(codes)
        self._show(self.codes_page)

    # --- sign-in ------------------------------------------------------------------------------
    def _login(self, username: str, password: str) -> None:
        try:
            with busy():
                pending = self.auth.login_password(username, password)
        except RestartRequired as exc:  # account locked
            self._restart(str(exc), "error")
            return
        except AuthError as exc:
            self.login_page.password.clear()
            self.login_page.show_message(str(exc))
            self.login_page.password.setFocus()
            return
        if isinstance(pending, PendingEnrollment):
            self._start_enrollment(pending)
        else:
            self.pending = pending
            self._show(self.otp_page)

    def _second_factor(self, verify, code: str) -> None:
        if self.pending is None or self.stack.currentWidget() is not self.otp_page:
            return  # stray signal (e.g. Enter pressed right after the auto-submit)
        try:
            session = verify(self.pending, code)
        except RestartRequired as exc:
            self._restart(str(exc), "error")
            return
        except AuthError as exc:
            self.otp_page.code.clear()
            self.otp_page.recovery.clear()
            self.otp_page.show_message(str(exc))
            return
        self.pending = None
        self.session = session
        self._enter_home()

    # --- signed in ------------------------------------------------------------------------------
    def _enter_home(self) -> None:
        if not self.auth.is_session_valid(self.session):
            self._restart("Please sign in again.", "error")
            return
        self.home_page.session = self.session
        self._show(self.home_page)
        self._session_timer.start()

    def logout(self, message: str = "") -> None:
        self._session_timer.stop()
        if self.session is not None:
            self.auth.logout(self.session)
        self.session = None
        self.home_page.session = None
        self._restart(message, "info")

    def _check_session(self) -> None:
        if self.session is not None and not self.auth.is_session_valid(self.session):
            self.logout("Your session expired after a period of inactivity. Please sign in again.")

    # --- Qt overrides -----------------------------------------------------------------------------
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        session = getattr(self, "session", None)
        if session is not None and event.type() in self.ACTIVITY_EVENTS:
            if not self.auth.touch(session):
                QTimer.singleShot(0, self._check_session)
        return False  # never swallow the event

    def closeEvent(self, event) -> None:
        QApplication.instance().removeEventFilter(self)
        self._session_timer.stop()
        if self.session is not None:
            self.auth.logout(self.session)
        self._close_pending()
        super().closeEvent(event)


# ---------------------------------------------------------------------------------------- app
def _apply_light_appearance(app: QApplication) -> None:
    """The window must be white: force the light look even when macOS is in Dark Mode."""
    hints = app.styleHints()
    if hasattr(hints, "setColorScheme"):  # Qt >= 6.8
        hints.setColorScheme(Qt.ColorScheme.Light)
    palette = QPalette()
    for role, color in {
        QPalette.ColorRole.Window: "#ffffff", QPalette.ColorRole.WindowText: "#1d1d1f",
        QPalette.ColorRole.Base: "#ffffff", QPalette.ColorRole.AlternateBase: "#f5f5f7",
        QPalette.ColorRole.Text: "#1d1d1f", QPalette.ColorRole.Button: "#f5f5f7",
        QPalette.ColorRole.ButtonText: "#1d1d1f", QPalette.ColorRole.PlaceholderText: "#8e8e93",
        QPalette.ColorRole.Highlight: "#0071e3", QPalette.ColorRole.HighlightedText: "#ffffff",
        QPalette.ColorRole.ToolTipBase: "#ffffff", QPalette.ColorRole.ToolTipText: "#1d1d1f",
    }.items():
        palette.setColor(role, QColor(color))
    app.setPalette(palette)
    app.setStyleSheet(STYLE)


def _install_error_handler(log_file: Path) -> None:
    """Packaged apps have no console: write unexpected errors to a log file and say where."""
    logging.basicConfig(filename=log_file, level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    def handler(exc_type, exc, tb) -> None:
        logging.getLogger("secureapp").critical("Unhandled error", exc_info=(exc_type, exc, tb))
        if QApplication.instance() is not None:
            QMessageBox.critical(None, config.APP_NAME, f"Unexpected error: {exc}\n\nDetails: {log_file}")

    sys.excepthook = handler


def run(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    if "--selftest" in argv:  # used by build_mac.sh to check the packaged app
        from .selftest import run_selftest
        return run_selftest()

    data_dir = config.data_dir()
    data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    _install_error_handler(data_dir / "app.log")
    app = QApplication(argv)
    app.setApplicationName(config.APP_NAME)
    app.setApplicationVersion(config.APP_VERSION)
    _apply_light_appearance(app)
    try:
        store = Store(data_dir / "secureapp.db")
    except Exception as exc:  # e.g. permissions on the data folder
        log.exception("Cannot open the database")
        QMessageBox.critical(None, config.APP_NAME, f"Cannot open the database:\n{exc}")
        return 1
    window = MainWindow(AuthService(store))
    window.show()
    window.raise_()
    window.activateWindow()
    exit_code = app.exec()
    store.close()
    return exit_code
