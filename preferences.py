from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
)

KEYRING_SERVICE = "OrganizadorPessoal"
KEYRING_USER = "smtp"


def _settings():
    return QSettings("OrganizadorPessoal", "LifeDashboard")


def _get_password():
    try:
        import keyring
        password = keyring.get_password(KEYRING_SERVICE, KEYRING_USER)
        if password:
            return password
    except Exception:
        pass
    return _settings().value("smtp_pass", "")


def _set_password(password):
    if not password:
        return
    try:
        import keyring
        keyring.set_password(KEYRING_SERVICE, KEYRING_USER, password)
        _settings().setValue("smtp_pass", "")
        return
    except Exception:
        pass
    _settings().setValue("smtp_pass", password)


def load_smtp_settings():
    settings = _settings()
    return {
        "server": settings.value("smtp_server", ""),
        "port": int(settings.value("smtp_port", 0) or 0),
        "user": settings.value("smtp_user", ""),
        "password": _get_password(),
        "from": settings.value("smtp_from", ""),
        "to": settings.value("smtp_to", ""),
    }


def save_smtp_settings(values):
    settings = _settings()
    settings.setValue("smtp_server", values.get("server", ""))
    settings.setValue("smtp_port", int(values.get("port", 0) or 0))
    settings.setValue("smtp_user", values.get("user", ""))
    settings.setValue("smtp_from", values.get("from", ""))
    settings.setValue("smtp_to", values.get("to", ""))
    _set_password(values.get("password", ""))


class PreferencesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferências")
        self.setMinimumWidth(360)

        form = QFormLayout(self)
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Escuro", "dark")
        self.theme_combo.addItem("Claro", "light")
        form.addRow("Tema:", self.theme_combo)

        self.font_spin = QSpinBox()
        self.font_spin.setRange(8, 20)
        form.addRow("Tamanho da fonte:", self.font_spin)

        self.tray_check = QCheckBox("Notificações na bandeja do sistema")
        form.addRow(self.tray_check)
        self.sound_check = QCheckBox("Sons de notificação")
        form.addRow(self.sound_check)
        self.email_check = QCheckBox("Enviar notificação por e-mail")
        form.addRow(self.email_check)
        smtp_btn = QPushButton("Configurar SMTP...")
        smtp_btn.clicked.connect(self._open_smtp)
        form.addRow(smtp_btn)
        self.contrast_check = QCheckBox("Alto contraste")
        form.addRow(self.contrast_check)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def set_values(self, theme, font_size):
        idx = self.theme_combo.findData(theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        self.font_spin.setValue(int(font_size))

    def _open_smtp(self):
        dialog = SMTPDialog(self)
        current = load_smtp_settings()
        dialog.set_values(
            current.get("server"),
            current.get("port"),
            current.get("user"),
            current.get("from"),
            current.get("to"),
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            save_smtp_settings(dialog.result())

    def result(self):
        return {
            "theme": self.theme_combo.currentData(),
            "font_size": self.font_spin.value(),
            "notify_tray": self.tray_check.isChecked(),
            "notify_sound": self.sound_check.isChecked(),
            "notify_email": self.email_check.isChecked(),
            "high_contrast": self.contrast_check.isChecked(),
        }


class SMTPDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar SMTP")
        form = QFormLayout(self)
        self.server_edit = QLineEdit()
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.user_edit = QLineEdit()
        self.pass_edit = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.from_edit = QLineEdit()
        self.to_edit = QLineEdit()
        form.addRow("Servidor SMTP:", self.server_edit)
        form.addRow("Porta:", self.port_spin)
        form.addRow("Usuário:", self.user_edit)
        form.addRow("Senha:", self.pass_edit)
        form.addRow("Remetente:", self.from_edit)
        form.addRow("Destinatário:", self.to_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def set_values(self, server, port, user, frm, to):
        self.server_edit.setText(server or "")
        try:
            self.port_spin.setValue(int(port) if port else 0)
        except Exception:
            self.port_spin.setValue(0)
        self.user_edit.setText(user or "")
        self.from_edit.setText(frm or "")
        self.to_edit.setText(to or "")

    def result(self):
        return {
            "server": self.server_edit.text().strip(),
            "port": int(self.port_spin.value()),
            "user": self.user_edit.text().strip(),
            "password": self.pass_edit.text(),
            "from": self.from_edit.text().strip(),
            "to": self.to_edit.text().strip(),
        }
