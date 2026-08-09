import sys

import qtawesome as qta
from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QSettings, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QKeySequence, QPainter, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSystemTrayIcon,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

import notify
import preferences
import reminders as rem
import tasks as tasks_mod
import theme
from agenda_ui import AgendaView
from dashboard_ui import DashboardView
from news import NewsView
from reminders_ui import RemindersView
from tasks_ui import TasksView
from weather_ui import WeatherView


def _as_bool(value):
    return value in (True, "true", "1", "True", 1)


class Sidebar(QWidget):
    currentRowChanged = Signal(int)

    def __init__(self, entries, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(60)
        self._entries = entries
        self._buttons = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 10, 6, 10)
        layout.setSpacing(2)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        for row, (name, icon_name, enabled) in enumerate(entries):
            btn = QToolButton()
            btn.setObjectName("sidebarBtn")
            btn.setIconSize(QSize(22, 22))
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            btn.setToolTip(name)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setCheckable(enabled)
            btn.setEnabled(enabled)
            btn.setFixedSize(44, 44)
            btn.setIcon(qta.icon(icon_name, color=theme.ACCENT if enabled else theme.SIDEBAR_DISABLED))
            self._group.addButton(btn, row)
            btn.clicked.connect(lambda checked=False, r=row: self._on_clicked(r))
            layout.addWidget(btn, 0, Qt.AlignmentFlag.AlignHCenter)
            self._buttons.append(btn)

        layout.addStretch()
        self._group.idClicked.connect(self._set_current)

    def add_footer(self, footer_layout):
        self.layout().addLayout(footer_layout)

    def _on_clicked(self, row):
        self._set_current(row)

    def _set_current(self, row):
        btn = self._buttons[row]
        if not btn.isEnabled():
            return
        btn.setChecked(True)
        self.currentRowChanged.emit(row)

    def setCurrentRow(self, row):
        self._set_current(row)

    def currentRow(self):
        checked = self._group.checkedId()
        return checked if checked >= 0 else 0

    def refresh_icons(self):
        for row, (_, icon_name, enabled) in enumerate(self._entries):
            self._buttons[row].setIcon(
                qta.icon(icon_name, color=theme.ACCENT if enabled else theme.SIDEBAR_DISABLED)
            )


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Organizador Pessoal")
        self.resize(1100, 760)

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._sidebar_entries = (
            ("Início", "fa5s.home", True),
            ("Notícias", "fa5s.newspaper", True),
            ("Lembretes", "fa5s.bell", True),
            ("Clima", "fa5s.cloud-sun", True),
            ("Tarefas", "fa5s.tasks", True),
            ("Agenda", "fa5s.calendar-alt", True),
            ("Notas", "fa5s.sticky-note", False),
        )

        self.theme_btn = QToolButton()
        self.theme_btn.setObjectName("themeBtn")
        self.theme_btn.setIconSize(QSize(20, 20))
        self.theme_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_btn.clicked.connect(self._toggle_theme)
        self._update_theme_btn()

        self.settings_btn = QToolButton()
        self.settings_btn.setObjectName("settingsBtn")
        self.settings_btn.setIconSize(QSize(20, 20))
        self.settings_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.setIcon(qta.icon("fa5s.cog", color=theme.ACCENT))
        self.settings_btn.setToolTip("Preferências")
        self.settings_btn.clicked.connect(self._open_preferences)

        self.sidebar = Sidebar(self._sidebar_entries)
        self.sidebar.currentRowChanged.connect(self._switch_view)

        sidebar_footer = QVBoxLayout()
        sidebar_footer.setContentsMargins(0, 0, 0, 0)
        sidebar_footer.setSpacing(2)
        separator = QFrame()
        separator.setObjectName("sidebarSep")
        separator.setFixedHeight(1)
        sidebar_footer.addWidget(separator)
        sidebar_footer.addWidget(self.settings_btn, 0, Qt.AlignmentFlag.AlignHCenter)
        sidebar_footer.addWidget(self.theme_btn, 0, Qt.AlignmentFlag.AlignHCenter)
        self.sidebar.add_footer(sidebar_footer)

        self.stack = QWidget()
        self.stack_layout = QVBoxLayout(self.stack)
        self.stack_layout.setContentsMargins(24, 20, 24, 20)

        root.addWidget(self.sidebar)
        root.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        self.reminder_manager = rem.ReminderManager()
        self.tasks_manager = tasks_mod.TaskManager()
        self.dashboard_view = DashboardView(self.reminder_manager, self.tasks_manager)
        self.news_view = NewsView()
        self.reminders_view = RemindersView(self.reminder_manager)
        self.tasks_view = TasksView(self.tasks_manager)
        self.agenda_view = AgendaView(self.tasks_manager)
        self.weather_view = WeatherView()
        self.stack_layout.addWidget(self.dashboard_view)
        self.stack_layout.addWidget(self.news_view)
        self.stack_layout.addWidget(self.reminders_view)
        self.stack_layout.addWidget(self.weather_view)
        self.stack_layout.addWidget(self.tasks_view)
        self.stack_layout.addWidget(self.agenda_view)
        self.dashboard_view.hide()
        self.reminders_view.hide()
        self.weather_view.hide()
        self.tasks_view.hide()
        self.agenda_view.hide()

        self._fade_effect = None
        self._fade_anim = None

        self.dashboard_view.open_news.connect(lambda: self.sidebar.setCurrentRow(1))
        self.dashboard_view.open_reminders.connect(lambda: self.sidebar.setCurrentRow(2))
        self.dashboard_view.open_weather.connect(lambda: self.sidebar.setCurrentRow(3))
        self.dashboard_view.open_tasks.connect(lambda: self.sidebar.setCurrentRow(4))
        self.dashboard_view.open_agenda.connect(lambda: self.sidebar.setCurrentRow(5))
        self.dashboard_view.new_task_requested.connect(self._new_task)
        self.dashboard_view.new_reminder_requested.connect(self._new_reminder)

        self.sidebar.setCurrentRow(0)
        self._switch_view(self.sidebar.currentRow())

        self._email_worker = None
        self._notif_popups = []
        self._setup_tray()
        self._setup_scheduler()
        self._setup_shortcuts()

    def _update_theme_btn(self):
        if theme.CURRENT_THEME == "dark":
            self.theme_btn.setIcon(qta.icon("fa5s.sun", color=theme.ACCENT_HOVER))
            self.theme_btn.setToolTip("Mudar para tema claro")
        else:
            self.theme_btn.setIcon(qta.icon("fa5s.moon", color=theme.ACCENT))
            self.theme_btn.setToolTip("Mudar para tema escuro")

    def _apply_sidebar_icons(self):
        self.sidebar.refresh_icons()

    def _toggle_theme(self):
        new_theme = "light" if theme.CURRENT_THEME == "dark" else "dark"
        app = QApplication.instance()
        theme.apply_theme(app, new_theme)
        self._update_theme_btn()
        self._apply_sidebar_icons()
        self._refresh_lists()
        QSettings("OrganizadorPessoal", "LifeDashboard").setValue("theme", new_theme)
        if self._tray is not None:
            self._update_tray_icon()

    def _refresh_lists(self):
        self.dashboard_view.refresh()
        self.reminders_view.refresh()
        self.tasks_view.refresh()
        self.agenda_view.refresh()

    def _setup_shortcuts(self):
        for index in range(1, 7):
            QShortcut(QKeySequence(f"Ctrl+{index}"), self,
                      activated=lambda i=index: self.sidebar.setCurrentRow(i - 1))
        QShortcut(QKeySequence("F5"), self, activated=self._refresh_current)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self._focus_search)
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self._new_task)
        QShortcut(QKeySequence("Ctrl+="), self, activated=self._zoom_in)
        QShortcut(QKeySequence("Ctrl++"), self, activated=self._zoom_in)
        QShortcut(QKeySequence("Ctrl+-"), self, activated=self._zoom_out)
        QShortcut(QKeySequence("Ctrl+0"), self, activated=self._zoom_reset)

    def _refresh_current(self):
        row = self.sidebar.currentRow()
        if row == 0:
            self.dashboard_view.refresh()
        elif row == 1:
            self.news_view.load_news()
        elif row == 3:
            self.weather_view.load_weather()
        elif row == 5:
            self.agenda_view.refresh()

    def _focus_search(self):
        row = self.sidebar.currentRow()
        target = {
            1: self.news_view.search_edit,
            2: self.reminders_view.search_edit,
            4: self.tasks_view.search_edit,
            5: self.agenda_view.search_edit,
        }.get(row)
        if target is not None:
            target.setFocus()
            target.selectAll()

    def _new_task(self):
        self.sidebar.setCurrentRow(4)
        self.tasks_view._add_task()

    def _new_reminder(self):
        self.sidebar.setCurrentRow(2)
        self.reminders_view._add_reminder()

    def _zoom_in(self):
        self._set_zoom(theme.FONT_SCALE + 0.1)

    def _zoom_out(self):
        self._set_zoom(theme.FONT_SCALE - 0.1)

    def _zoom_reset(self):
        self._set_zoom(1.0)

    def _set_zoom(self, scale):
        theme.apply_font_scale(QApplication.instance(), scale)
        QSettings("OrganizadorPessoal", "LifeDashboard").setValue("font_scale", theme.FONT_SCALE)
        self._refresh_lists()

    def _setup_tray(self):
        self._tray = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self._tray = QSystemTrayIcon(QIcon(self._tray_pixmap()), self)
            self._tray.setToolTip("Organizador Pessoal")
            menu = QMenu()
            show_action = menu.addAction(qta.icon("fa5s.window-restore", color=theme.ACCENT), "Mostrar / Ocultar")
            show_action.triggered.connect(self._toggle_window)
            menu.addSeparator()
            news_action = menu.addAction(qta.icon("fa5s.newspaper", color=theme.ACCENT), "Atualizar notícias")
            news_action.triggered.connect(self.news_view.load_news)
            weather_action = menu.addAction(qta.icon("fa5s.cloud-sun", color=theme.ACCENT), "Atualizar clima")
            weather_action.triggered.connect(self.weather_view.load_weather)
            menu.addSeparator()
            task_action = menu.addAction(qta.icon("fa5s.plus", color=theme.ACCENT), "Nova tarefa")
            task_action.triggered.connect(self._new_task)
            reminder_action = menu.addAction(qta.icon("fa5s.bell", color=theme.ACCENT), "Novo lembrete")
            reminder_action.triggered.connect(self._new_reminder)
            menu.addSeparator()
            prefs_action = menu.addAction(qta.icon("fa5s.cog", color=theme.ACCENT), "Preferências…")
            prefs_action.triggered.connect(self._open_preferences)
            quit_action = menu.addAction(qta.icon("fa5s.power-off", color=theme.DANGER), "Sair")
            quit_action.triggered.connect(QApplication.instance().quit)
            self._tray.setContextMenu(menu)
            self._tray.activated.connect(self._tray_activated)
            self._tray.show()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._toggle_window()

    def _toggle_window(self):
        if self.isVisible():
            self.hide()
        else:
            self.showNormal()
            self.raise_()
            self.activateWindow()

    def _update_tray_icon(self):
        if self._tray is not None:
            self._tray.setIcon(QIcon(self._tray_pixmap()))

    def _tray_pixmap(self):
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(theme.ACCENT))
        painter.drawEllipse(8, 8, 48, 48)
        painter.end()
        return pixmap

    def _setup_scheduler(self):
        self._alarm_timer = QTimer(self)
        self._alarm_timer.setInterval(15000)
        self._alarm_timer.timeout.connect(self._check_alarms)
        self._alarm_timer.start()

    def _show_notifications(self, fired):
        for reminder in fired:
            if theme.NOTIFY_SOUND:
                notify.play_type_sound(reminder.trigger_type)
            if not theme.NOTIFY_TRAY:
                continue
            message = reminder.title
            if reminder.description:
                message += f"\n{reminder.description}"
            popup = notify.show_notification(
                "Lembrete",
                message,
                snooze_cb=lambda minutes, rid=reminder.id: self.reminder_manager.snooze(rid, minutes),
            )
            self._notif_popups.append(popup)
            popup.destroyed.connect(
                lambda obj=None, p=popup: self._notif_popups.remove(p) if p in self._notif_popups else None
            )

    def _check_alarms(self):
        fired = self.reminder_manager.check_due()
        if not fired:
            return
        self._show_notifications(fired)

        if self._email_worker is not None and self._email_worker.isRunning():
            return
        smtp = preferences.load_smtp_settings()
        if smtp.get("server") and smtp.get("to"):
            lines = [f"⏰ {r.title}" for r in fired]
            message = "\n".join(lines)
            self._email_worker = notify.EmailWorker(
                smtp,
                "Lembrete(s) - Organizador Pessoal",
                message,
                self,
            )
            self._email_worker.failed.connect(self._email_failed)
            self._email_worker.start()
        self._refresh_lists()

    def _email_failed(self, error):
        QMessageBox.warning(self, "Falha ao enviar e-mail", f"Erro ao enviar notificação por e-mail:\n{error}")

    def closeEvent(self, event):
        self._alarm_timer.stop()
        self.dashboard_view.shutdown()
        self.news_view.shutdown()
        self.weather_view.shutdown()
        super().closeEvent(event)

    def _switch_view(self, row):
        self.dashboard_view.setVisible(row == 0)
        self.news_view.setVisible(row == 1)
        self.reminders_view.setVisible(row == 2)
        self.weather_view.setVisible(row == 3)
        self.tasks_view.setVisible(row == 4)
        self.agenda_view.setVisible(row == 5)
        self._start_fade()

    def _start_fade(self):
        if self._fade_anim is not None:
            self._fade_anim.stop()
            self._fade_anim = None
        self._fade_effect = None
        effect = QGraphicsOpacityEffect()
        effect.setOpacity(0.0)
        self.stack.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(150)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        anim.finished.connect(lambda: self._finish_fade(effect))
        self._fade_anim = anim
        anim.start()

    def _finish_fade(self, effect):
        if self.stack.graphicsEffect() is effect:
            self.stack.setGraphicsEffect(None)
        self._fade_anim = None

    def _open_preferences(self):
        dialog = preferences.PreferencesDialog(self)
        settings = QSettings("OrganizadorPessoal", "LifeDashboard")
        saved_theme = settings.value("theme", theme.CURRENT_THEME)
        saved_font = int(settings.value("font_size", theme.FONT_SIZE))
        dialog.set_values(saved_theme, saved_font)
        dialog.tray_check.setChecked(_as_bool(settings.value("notify_tray", True)))
        dialog.sound_check.setChecked(_as_bool(settings.value("notify_sound", True)))
        dialog.email_check.setChecked(_as_bool(settings.value("notify_email", False)))
        dialog.contrast_check.setChecked(_as_bool(settings.value("high_contrast", False)))
        if dialog.exec() == QDialog.DialogCode.Accepted:
            res = dialog.result()
            settings.setValue("theme", res["theme"])
            settings.setValue("font_size", res["font_size"])
            settings.setValue("notify_tray", res.get("notify_tray", True))
            settings.setValue("notify_sound", res.get("notify_sound", True))
            settings.setValue("notify_email", res.get("notify_email", False))
            settings.setValue("high_contrast", res.get("high_contrast", False))
            theme.FONT_SIZE = int(res["font_size"])
            theme.NOTIFY_TRAY = bool(res.get("notify_tray", True))
            theme.NOTIFY_SOUND = bool(res.get("notify_sound", True))
            theme.HIGH_CONTRAST = bool(res.get("high_contrast", False))
            app = QApplication.instance()
            theme.apply_theme(app, res["theme"])
            self._update_theme_btn()
            self._apply_sidebar_icons()
            self._refresh_lists()


def main():
    app = QApplication(sys.argv)
    settings = QSettings("OrganizadorPessoal", "LifeDashboard")
    saved_theme = settings.value("theme", "dark")
    try:
        theme.FONT_SIZE = int(settings.value("font_size", theme.FONT_SIZE))
    except Exception:
        pass
    try:
        theme.set_font_scale(float(settings.value("font_scale", 1.0)))
    except Exception:
        pass
    theme.NOTIFY_TRAY = _as_bool(settings.value("notify_tray", True))
    theme.NOTIFY_SOUND = _as_bool(settings.value("notify_sound", True))
    theme.HIGH_CONTRAST = _as_bool(settings.value("high_contrast", False))
    theme.apply_theme(app, saved_theme)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
