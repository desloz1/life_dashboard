import smtplib
from email.message import EmailMessage

from PySide6.QtCore import QTimer, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

TYPE_SOUNDS = {
    "one_time": (880, 200),
    "daily": (660, 200),
    "weekly": (550, 220),
    "monthly": (440, 260),
}


def play_type_sound(trigger_type):
    """Toca um tom diferente por tipo de lembrete."""
    frequency, duration = TYPE_SOUNDS.get(trigger_type, (700, 200))
    try:
        import winsound

        winsound.Beep(frequency, duration)
    except Exception:
        try:
            QApplication.beep()
        except Exception:
            pass


_open_popups = []


def show_notification(title, message, snooze_cb=None, parent=None):
    """Exibe um popup flutuante no canto inferior direito com botão de soneca."""
    popup = NotificationPopup(title, message, snooze_cb, parent=parent)
    _open_popups.append(popup)
    popup.destroyed.connect(
        lambda obj=None, p=popup: _open_popups.remove(p) if p in _open_popups else None
    )
    popup.show()
    popup._reposition()
    return popup


class NotificationPopup(QWidget):
    def __init__(self, title, message, snooze_cb=None, parent=None):
        super().__init__(parent)
        self.setObjectName("notifPopup")
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setFixedWidth(340)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setObjectName("notifTitle")
        layout.addWidget(title_label)

        message_label = QLabel(message)
        message_label.setObjectName("notifMsg")
        message_label.setWordWrap(True)
        layout.addWidget(message_label)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addStretch()
        if snooze_cb is not None:
            snooze_btn = QPushButton(" Soneca")
            snooze_btn.setObjectName("secondaryBtn")
            snooze_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            menu = QMenu(snooze_btn)
            for minutes in (5, 15, 30):
                action = menu.addAction(f"Adiar {minutes} min")
                action.triggered.connect(lambda checked=False, m=minutes: self._snooze(snooze_cb, m))
            snooze_btn.setMenu(menu)
            buttons.addWidget(snooze_btn)
        ok_btn = QPushButton(" Entendi")
        ok_btn.setObjectName("toggleBtn")
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.clicked.connect(self.close)
        buttons.addWidget(ok_btn)
        layout.addLayout(buttons)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.close)
        self._timer.start(12000)

    def _snooze(self, callback, minutes):
        try:
            callback(minutes)
        finally:
            self.close()

    def _reposition(self):
        screen = QApplication.primaryScreen().availableGeometry()
        index = _open_popups.index(self) if self in _open_popups else 0
        x = screen.right() - self.width() - 16
        y = screen.bottom() - self.height() - 16 - index * (self.height() + 8)
        self.move(x, max(screen.top(), y))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.close()
        super().mouseReleaseEvent(event)


def send_email_notification(server, port, user, password, frm, to, subject, body):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = frm
    msg["To"] = to
    msg.set_content(body)

    if port == 465:
        with smtplib.SMTP_SSL(server, port, timeout=10) as smtp:
            if user and password:
                smtp.login(user, password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(server, port, timeout=10) as smtp:
            smtp.ehlo()
            try:
                smtp.starttls()
                smtp.ehlo()
            except Exception:
                pass
            if user and password:
                smtp.login(user, password)
            smtp.send_message(msg)


class EmailWorker(QThread):
    failed = Signal(str)

    def __init__(self, settings, subject, body, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._subject = subject
        self._body = body

    def run(self):
        try:
            send_email_notification(
                self._settings.get("server"),
                self._settings.get("port", 0),
                self._settings.get("user"),
                self._settings.get("password"),
                self._settings.get("from") or self._settings.get("user"),
                self._settings.get("to"),
                self._subject,
                self._body,
            )
        except Exception as exc:
            self.failed.emit(str(exc))
