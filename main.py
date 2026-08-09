import datetime
import sys

import qtawesome as qta
import requests
from PySide6.QtCore import QByteArray, QDate, QRectF, QSettings, QSize, Qt, QThread, QTime, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QFont, QIcon, QPainter, QPainterPath, QPalette, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QSystemTrayIcon,
    QTimeEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

import reminders as rem
import scraper
import weather

THUMB_WIDTH = 130
THUMB_HEIGHT = 90

DARK_THEME = {
    "ACCENT": "#5b8cff",
    "ACCENT_HOVER": "#7aa2ff",
    "ACCENT_DARK": "#3f6ee0",
    "ACCENT_SOFT": "#2b3a5e",
    "BG": "#0f1115",
    "SURFACE": "#171a21",
    "CARD": "#1c2027",
    "CARD_HOVER": "#1f2430",
    "BORDER": "#262b35",
    "BORDER_HOVER": "#3b4a6e",
    "TEXT": "#e8ecf3",
    "MUTED": "#8a93a6",
    "DANGER": "#ff6b6b",
    "DANGER_SOFT": "#3a2328",
    "DANGER_HOVER": "#4a2a30",
    "BEVEL_LIGHT": "#394152",
    "BEVEL_DARK": "#0a0c10",
    "SHADOW_COLOR": (0, 0, 0, 150),
    "BTN": "#222837",
    "BTN_HOVER": "#2a3142",
    "BTN_PRESSED": "#1d2330",
    "BTN_DISABLED": "#20242e",
    "BTN_DISABLED_TEXT": "#5a6375",
    "INPUT": "#12151b",
    "TOGGLE_BTN": "#22314f",
    "TOGGLE_BTN_HOVER": "#2b3f66",
    "SECONDARY_BTN": "#232a36",
    "SECONDARY_BTN_HOVER": "#2c3442",
    "SIDEBAR_SELECTED": "#2b3a5e",
    "SIDEBAR_HOVER": "#232a36",
    "SIDEBAR_DISABLED": "#4a5262",
    "SCROLL_HANDLE": "#333c50",
    "SCROLL_HANDLE_HOVER": "#414c66",
    "THUMB_BG": "#222834",
    "PAUSED_BG": "#191c22",
    "PAUSED_BORDER": "#2a2f3a",
    "PLACEHOLDER": "#5a6375",
}

LIGHT_THEME = {
    "ACCENT": "#1a73e8",
    "ACCENT_HOVER": "#1557b0",
    "ACCENT_DARK": "#0d5cb8",
    "ACCENT_SOFT": "#e3f0fd",
    "BG": "#f4f6f9",
    "SURFACE": "#ffffff",
    "CARD": "#ffffff",
    "CARD_HOVER": "#fbfdff",
    "BORDER": "#e2e6ec",
    "BORDER_HOVER": "#aecdf5",
    "TEXT": "#1a1f2b",
    "MUTED": "#5f6b7a",
    "DANGER": "#d93025",
    "DANGER_SOFT": "#fdecea",
    "DANGER_HOVER": "#f8d7d5",
    "BEVEL_LIGHT": "#ffffff",
    "BEVEL_DARK": "#c6cfda",
    "SHADOW_COLOR": (45, 63, 92, 60),
    "BTN": "#eef1f5",
    "BTN_HOVER": "#e3e8ef",
    "BTN_PRESSED": "#d8dee7",
    "BTN_DISABLED": "#eceef2",
    "BTN_DISABLED_TEXT": "#a0a8b5",
    "INPUT": "#ffffff",
    "TOGGLE_BTN": "#e3f0fd",
    "TOGGLE_BTN_HOVER": "#cfe3fb",
    "SECONDARY_BTN": "#eef1f5",
    "SECONDARY_BTN_HOVER": "#e3e8ef",
    "SIDEBAR_SELECTED": "#e3f0fd",
    "SIDEBAR_HOVER": "#f0f4f8",
    "SIDEBAR_DISABLED": "#b6bdc9",
    "SCROLL_HANDLE": "#c3cbd8",
    "SCROLL_HANDLE_HOVER": "#a9b4c4",
    "THUMB_BG": "#eef1f4",
    "PAUSED_BG": "#f7f8fa",
    "PAUSED_BORDER": "#e6e9ee",
    "PLACEHOLDER": "#9aa4b2",
}

CURRENT_THEME = "dark"


def apply_theme(app, name):
    global CURRENT_THEME
    CURRENT_THEME = "dark" if name == "dark" else "light"
    globals().update(THEMES[CURRENT_THEME])
    apply_stylesheet(app)


THEMES = {"dark": DARK_THEME, "light": LIGHT_THEME}


def load_pixmap(url):
    if not url:
        return None
    try:
        response = requests.get(url, headers=scraper.HEADERS, timeout=10)
        if response.status_code != 200:
            return None
        pixmap = QPixmap()
        pixmap.loadFromData(QByteArray(response.content))
        if pixmap.isNull():
            return None
        return pixmap.scaled(
            THUMB_WIDTH,
            THUMB_HEIGHT,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
    except requests.RequestException:
        return None


def rounded_pixmap(pixmap, radius=10):
    rounded = QPixmap(pixmap.size())
    rounded.fill(Qt.GlobalColor.transparent)
    painter = QPainter(rounded)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(QRectF(pixmap.rect()), radius, radius)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, pixmap)
    painter.end()
    return rounded


def icon(name, color=None, size=22):
    return qta.icon(name, color=color or ACCENT).pixmap(size, size)


def make_title(icon_name, text):
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(10)
    icon_label = QLabel()
    icon_label.setPixmap(icon(icon_name, ACCENT, 22))
    label = QLabel(text)
    label.setObjectName("pageTitle")
    layout.addWidget(icon_label)
    layout.addWidget(label)
    return widget


def make_shadow(widget, x=0, y=3, blur=18):
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(x, y)
    widget.setGraphicsEffect(effect)
    return effect


def apply_shadow_colors(app):
    for widget in app.allWidgets():
        if widget.objectName() in ("sidebar", "newsCard", "reminderCard"):
            effect = widget.graphicsEffect()
            if isinstance(effect, QGraphicsDropShadowEffect):
                effect.setColor(QColor(*SHADOW_COLOR))


class NewsWorker(QThread):
    finished_ok = Signal(list)
    failed = Signal(str)

    def __init__(self, show_thumbnails, parent=None):
        super().__init__(parent)
        self._show_thumbnails = show_thumbnails

    def run(self):
        raw = []
        errors = []
        for source in scraper.SOURCES:
            if self.isInterruptionRequested():
                return
            try:
                raw.extend(scraper.fetch_news(source, limit=10))
            except requests.RequestException as exc:
                errors.append(f"{source}: {exc}")
        if not raw:
            self.failed.emit("; ".join(errors) or "Nenhuma notícia carregada")
            return

        groups = {}
        for item in raw:
            groups.setdefault(item["source"], []).append(item)
        items = []
        for offset in range(max(len(group) for group in groups.values())):
            for source_items in groups.values():
                if offset < len(source_items):
                    items.append(source_items[offset])

        for item in items:
            item["show_thumb"] = self._show_thumbnails
            if self.isInterruptionRequested():
                return
            if self._show_thumbnails:
                item["pixmap"] = load_pixmap(item["image"])
            else:
                item["pixmap"] = None
        if not self.isInterruptionRequested():
            self.finished_ok.emit(items)


class NewsCard(QFrame):
    clicked = Signal(str)

    def __init__(self, item, parent=None):
        super().__init__(parent)
        self._url = item["url"]
        self.setObjectName("newsCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        make_shadow(self, y=3, blur=16)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(14)

        self.show_thumb = item.get("show_thumb", True)
        if self.show_thumb:
            self.thumb = QLabel()
            self.thumb.setFixedSize(THUMB_WIDTH, THUMB_HEIGHT)
            self.thumb.setObjectName("newsThumb")
            self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pixmap = item.get("pixmap")
            if pixmap is not None:
                self.thumb.setPixmap(rounded_pixmap(pixmap, 10))
            else:
                self.thumb.setPixmap(icon("fa5s.newspaper", "#6b7684", 40))
            layout.addWidget(self.thumb)

        text_col = QVBoxLayout()
        text_col.setSpacing(6)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(8)
        self.category = QLabel(item["category"])
        self.category.setObjectName("newsCategory")
        meta_row.addWidget(self.category)
        self.source_badge = QLabel(item.get("source") or "")
        self.source_badge.setObjectName("newsSource")
        meta_row.addWidget(self.source_badge)
        if item.get("date"):
            self.date = QLabel(item["date"])
            self.date.setObjectName("newsDate")
            meta_row.addWidget(self.date)
        meta_row.addStretch()
        text_col.addLayout(meta_row)

        self.title = QLabel(item["title"])
        self.title.setObjectName("newsTitle")
        self.title.setWordWrap(True)
        text_col.addWidget(self.title)
        text_col.addStretch()

        layout.addLayout(text_col, 1)
        self.setMinimumHeight(90 if not self.show_thumb else 120)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._url)
        super().mouseReleaseEvent(event)


class NewsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        title = make_title("fa5s.newspaper", "Notícias de Blumenau")
        self.status = QLabel("")
        self.status.setObjectName("status")

        self.refresh_btn = QPushButton(" Atualizar")
        self.refresh_btn.setIcon(qta.icon("fa5s.sync-alt", color="#ffffff"))
        self.refresh_btn.setIconSize(QSize(15, 15))
        self.refresh_btn.setObjectName("refreshBtn")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.load_news)

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.status)
        self.thumb_check = QCheckBox("Imagens")
        self.thumb_check.setCursor(Qt.CursorShape.PointingHandCursor)
        self.thumb_check.toggled.connect(self.load_news)
        header.addWidget(self.thumb_check)
        header.addWidget(self.refresh_btn)
        root.addLayout(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setObjectName("scrollArea")
        self.list_host = QWidget()
        self.list_layout = QVBoxLayout(self.list_host)
        self.list_layout.setContentsMargins(0, 0, 6, 6)
        self.list_layout.setSpacing(10)
        self.list_layout.addStretch()
        self.scroll.setWidget(self.list_host)
        root.addWidget(self.scroll, 1)

        self.load_news()

    def load_news(self):
        if self._worker and self._worker.isRunning():
            return
        self.status.setText("Carregando…")
        self.refresh_btn.setEnabled(False)
        self._clear_cards()

        self._worker = NewsWorker(self.thumb_check.isChecked(), self)
        self._worker.finished_ok.connect(self._on_loaded)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _clear_cards(self):
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _on_loaded(self, items):
        for item in items:
            card = NewsCard(item)
            card.clicked.connect(self._open_url)
            self.list_layout.insertWidget(self.list_layout.count() - 1, card)
        self.status.setText(f"{len(items)} notícias")

    def _on_failed(self, error):
        self.status.setText("Falha ao carregar notícias")
        label = QLabel(f"Não foi possível carregar as notícias.\n{error}")
        label.setObjectName("errorLabel")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.list_layout.insertWidget(0, label)

    def _on_finished(self):
        self.refresh_btn.setEnabled(True)

    def _open_url(self, url):
        QDesktopServices.openUrl(QUrl(url))

    def shutdown(self):
        if self._worker and self._worker.isRunning():
            self._worker.requestInterruption()
            if not self._worker.wait(2500):
                self._worker.terminate()
                self._worker.wait()


WEEKDAYS_FULL = [
    "Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira",
    "Sexta-feira", "Sábado", "Domingo",
]
WEEKDAYS_SHORT = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
MONTHS = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


def format_full_date(date):
    return (
        f"{WEEKDAYS_FULL[date.weekday()]}, {date.day} de {MONTHS[date.month - 1]} de {date.year}"
    )


class WeatherWorker(QThread):
    finished_ok = Signal(dict)
    failed = Signal(str)

    def run(self):
        try:
            data = weather.get_weather()
        except requests.RequestException as exc:
            if not self.isInterruptionRequested():
                self.failed.emit(str(exc))
            return
        if not self.isInterruptionRequested():
            self.finished_ok.emit(data)


class WeatherView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)

        header = QHBoxLayout()
        header.addWidget(make_title("fa5s.cloud-sun", "Clima · Blumenau"))
        header.addStretch()
        self.status = QLabel("")
        self.status.setObjectName("status")
        header.addWidget(self.status)
        self.refresh_btn = QPushButton(" Atualizar")
        self.refresh_btn.setIcon(qta.icon("fa5s.sync-alt", color="#ffffff"))
        self.refresh_btn.setIconSize(QSize(15, 15))
        self.refresh_btn.setObjectName("refreshBtn")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.load_weather)
        header.addWidget(self.refresh_btn)
        root.addLayout(header)

        self.clock_card = QFrame()
        self.clock_card.setObjectName("weatherCard")
        make_shadow(self.clock_card, y=3, blur=16)
        clock_layout = QVBoxLayout(self.clock_card)
        clock_layout.setContentsMargins(24, 18, 24, 18)
        clock_layout.setSpacing(2)
        self.time_label = QLabel("--:--:--")
        self.time_label.setObjectName("clockTime")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        clock_layout.addWidget(self.time_label)
        self.date_label = QLabel("")
        self.date_label.setObjectName("clockDate")
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        clock_layout.addWidget(self.date_label)
        root.addWidget(self.clock_card)

        self.current_card = QFrame()
        self.current_card.setObjectName("weatherCard")
        make_shadow(self.current_card, y=3, blur=16)
        self.current_layout = QVBoxLayout(self.current_card)
        self.current_layout.setContentsMargins(24, 18, 24, 18)
        root.addWidget(self.current_card)

        forecast_title = QLabel("Próximos 7 dias")
        forecast_title.setObjectName("pageTitle")
        root.addWidget(forecast_title)

        self.forecast_scroll = QScrollArea()
        self.forecast_scroll.setWidgetResizable(True)
        self.forecast_scroll.setObjectName("scrollArea")
        self.forecast_scroll.setFixedHeight(210)
        self.forecast_host = QWidget()
        self.forecast_row = QHBoxLayout(self.forecast_host)
        self.forecast_row.setContentsMargins(0, 0, 0, 0)
        self.forecast_row.setSpacing(10)
        self.forecast_scroll.setWidget(self.forecast_host)
        root.addWidget(self.forecast_scroll)

        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(1000)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start()
        self._update_clock()

        self._auto_timer = QTimer(self)
        self._auto_timer.setInterval(30 * 60 * 1000)
        self._auto_timer.timeout.connect(self.load_weather)
        self._auto_timer.start()

        self.load_weather()

    def _update_clock(self):
        now = datetime.datetime.now()
        self.time_label.setText(now.strftime("%H:%M:%S"))
        self.date_label.setText(format_full_date(now.date()))

    def load_weather(self):
        if self._worker and self._worker.isRunning():
            return
        self.status.setText("Carregando…")
        self.refresh_btn.setEnabled(False)
        self._clear_current()

        self._worker = WeatherWorker(self)
        self._worker.finished_ok.connect(self._on_loaded)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _clear_current(self):
        while self.current_layout.count():
            item = self.current_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        while self.forecast_row.count():
            item = self.forecast_row.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _on_loaded(self, data):
        current = QWidget()
        row = QHBoxLayout(current)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(20)

        weather_icon = QLabel()
        weather_icon.setPixmap(qta.icon(data["icon"], color=data["color"]).pixmap(72, 72))
        row.addWidget(weather_icon)

        temp = QLabel(f"{data['temperature']}°C")
        temp.setObjectName("weatherTemp")
        row.addWidget(temp)

        details = QVBoxLayout()
        details.setSpacing(4)
        desc = QLabel(data["description"])
        desc.setObjectName("weatherDesc")
        details.addWidget(desc)
        meta = QLabel(
            f"Sensação {data['feels_like']}°C    Umidade {data['humidity']}%    "
            f"Vento {data['wind']} km/h"
        )
        meta.setObjectName("weatherMeta")
        details.addWidget(meta)
        details.addStretch()
        row.addLayout(details)
        row.addStretch()

        self.current_layout.addWidget(current)

        for day in data["days"]:
            self.forecast_row.addWidget(self._build_day_card(day))
        self.forecast_row.addStretch()

        self.status.setText("Atualizado agora")

    def _build_day_card(self, day):
        date = datetime.date.fromisoformat(day["date"])
        card = QFrame()
        card.setObjectName("dayCard")
        make_shadow(card, y=3, blur=14)
        card.setFixedSize(120, 180)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        weekday = QLabel(WEEKDAYS_SHORT[date.weekday()])
        weekday.setObjectName("dayCardDay")
        weekday.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(weekday)

        day_date = QLabel(date.strftime("%d/%m"))
        day_date.setObjectName("dayCardDate")
        day_date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(day_date)

        icon_label = QLabel()
        icon_label.setPixmap(qta.icon(day["icon"], color=day["color"]).pixmap(40, 40))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        temps = QLabel(f"{day['max']}° / {day['min']}°")
        temps.setObjectName("dayCardTemp")
        temps.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(temps)

        precip = QLabel(f"💧 {day['precip']}%") if day["precip"] is not None else QLabel("")
        precip.setObjectName("dayCardPrecip")
        precip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(precip)
        return card

    def _on_failed(self, error):
        self.status.setText("Falha ao carregar o clima")
        label = QLabel(f"Não foi possível carregar o clima.\n{error}")
        label.setObjectName("errorLabel")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.current_layout.addWidget(label)

    def _on_finished(self):
        self.refresh_btn.setEnabled(True)

    def shutdown(self):
        if self._worker and self._worker.isRunning():
            self._worker.requestInterruption()
            if not self._worker.wait(2500):
                self._worker.terminate()
                self._worker.wait()


class ReminderDialog(QDialog):
    def __init__(self, manager, reminder=None, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.reminder = reminder
        self.setWindowTitle("Novo lembrete" if reminder is None else "Editar lembrete")
        self.setMinimumWidth(420)

        form = QFormLayout(self)
        form.setSpacing(10)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Título do lembrete")
        form.addRow("Título:", self.title_edit)

        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Descrição (opcional)")
        form.addRow("Descrição:", self.desc_edit)

        self.type_combo = QComboBox()
        self.type_combo.addItem("Única", "one_time")
        self.type_combo.addItem("Diária", "daily")
        self.type_combo.addItem("Semanal", "weekly")
        self.type_combo.addItem("Mensal", "monthly")
        form.addRow("Recorrência:", self.type_combo)

        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        form.addRow("Horário:", self.time_edit)

        self.detail_stack = QStackedWidget()

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        self.date_edit.setMinimumDate(QDate.currentDate())
        self.detail_stack.addWidget(self.date_edit)

        weekdays_widget = QWidget()
        weekdays_grid = QGridLayout(weekdays_widget)
        weekdays_grid.setContentsMargins(0, 0, 0, 0)
        self.weekday_checks = []
        for idx, name in enumerate(rem.WEEKDAY_NAMES):
            check = QCheckBox(name)
            weekdays_grid.addWidget(check, 0, idx)
            self.weekday_checks.append(check)
        self.detail_stack.addWidget(weekdays_widget)

        self.day_spin = QSpinBox()
        self.day_spin.setRange(1, 31)
        self.detail_stack.addWidget(self.day_spin)

        form.addRow("", self.detail_stack)

        self.enabled_check = QCheckBox("Lembrete ativo")
        self.enabled_check.setChecked(True)
        form.addRow("", self.enabled_check)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

        self.type_combo.currentIndexChanged.connect(self._update_detail_visibility)

        if reminder is not None:
            self.title_edit.setText(reminder.title)
            self.desc_edit.setText(reminder.description)
            self.time_edit.setTime(QTime.fromString(reminder.time, "HH:mm"))
            self.enabled_check.setChecked(reminder.enabled)
            type_index = self.type_combo.findData(reminder.trigger_type)
            self.type_combo.setCurrentIndex(type_index)
            if reminder.trigger_type == "one_time":
                self.date_edit.setDate(QDate.fromString(reminder.date, "yyyy-MM-dd"))
            elif reminder.trigger_type == "weekly":
                for idx, check in enumerate(self.weekday_checks):
                    check.setChecked(idx in reminder.weekdays)
            elif reminder.trigger_type == "monthly":
                self.day_spin.setValue(reminder.day_of_month)

        self._update_detail_visibility()

    def _update_detail_visibility(self):
        trigger_type = self.type_combo.currentData()
        if trigger_type == "one_time":
            self.detail_stack.setCurrentWidget(self.date_edit)
            self.detail_stack.show()
        elif trigger_type == "weekly":
            self.detail_stack.setCurrentWidget(self.weekday_checks[0].parentWidget())
            self.detail_stack.show()
        elif trigger_type == "monthly":
            self.detail_stack.setCurrentWidget(self.day_spin)
            self.detail_stack.show()
        else:
            self.detail_stack.hide()

    def _on_accept(self):
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "Lembrete", "Informe um título.")
            return
        trigger_type = self.type_combo.currentData()
        weekdays = [
            idx for idx, check in enumerate(self.weekday_checks) if check.isChecked()
        ]
        if trigger_type == "weekly" and not weekdays:
            QMessageBox.warning(self, "Lembrete", "Selecione pelo menos um dia da semana.")
            return

        self._result = {
            "title": title,
            "description": self.desc_edit.text().strip(),
            "trigger_type": trigger_type,
            "time": self.time_edit.time().toString("HH:mm"),
            "date": self.date_edit.date().toString("yyyy-MM-dd") if trigger_type == "one_time" else "",
            "weekdays": weekdays if trigger_type == "weekly" else [],
            "day_of_month": self.day_spin.value(),
            "enabled": self.enabled_check.isChecked(),
        }
        self.accept()

    def result_data(self):
        return getattr(self, "_result", None)


class ReminderCard(QFrame):
    edit_requested = Signal(str)
    delete_requested = Signal(str)
    toggle_requested = Signal(str)

    def __init__(self, reminder, parent=None):
        super().__init__(parent)
        self.setObjectName("reminderCard")
        if not reminder.enabled:
            self.setProperty("paused", True)
            self.style().unpolish(self)
            self.style().polish(self)
        make_shadow(self, y=3, blur=16)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(14)

        icon_label = QLabel()
        icon_label.setObjectName("reminderIcon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setPixmap(
            icon(
                "fa5s.bell" if reminder.enabled else "fa5s.bell-slash",
                ACCENT if reminder.enabled else MUTED,
                30,
            )
        )
        layout.addWidget(icon_label)

        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        self.title = QLabel(reminder.title)
        self.title.setObjectName("reminderTitle")
        text_col.addWidget(self.title)
        if reminder.description:
            self.desc = QLabel(reminder.description)
            self.desc.setObjectName("reminderDesc")
            self.desc.setWordWrap(True)
            text_col.addWidget(self.desc)
        schedule = rem.describe_schedule(reminder)
        self.schedule = QLabel(schedule)
        self.schedule.setObjectName("reminderSchedule")
        text_col.addWidget(self.schedule)
        self.next = QLabel(rem.format_next(reminder.next_trigger))
        self.next.setObjectName("reminderNext")
        text_col.addWidget(self.next)
        text_col.addStretch()
        layout.addLayout(text_col, 1)

        buttons = QVBoxLayout()
        buttons.setSpacing(6)
        toggle_btn = QPushButton(" Pausar" if reminder.enabled else " Ativar")
        toggle_btn.setObjectName("toggleBtn")
        toggle_btn.setIcon(qta.icon("fa5s.pause" if reminder.enabled else "fa5s.play", color=ACCENT))
        toggle_btn.setIconSize(QSize(13, 13))
        toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        toggle_btn.clicked.connect(lambda: self.toggle_requested.emit(reminder.id))
        edit_btn = QPushButton(" Editar")
        edit_btn.setObjectName("secondaryBtn")
        edit_btn.setIcon(qta.icon("fa5s.pen", color=TEXT))
        edit_btn.setIconSize(QSize(13, 13))
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.clicked.connect(lambda: self.edit_requested.emit(reminder.id))
        delete_btn = QPushButton(" Excluir")
        delete_btn.setObjectName("dangerBtn")
        delete_btn.setIcon(qta.icon("fa5s.trash-alt", color=DANGER))
        delete_btn.setIconSize(QSize(13, 13))
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.clicked.connect(lambda: self.delete_requested.emit(reminder.id))
        buttons.addWidget(toggle_btn)
        buttons.addWidget(edit_btn)
        buttons.addWidget(delete_btn)
        layout.addLayout(buttons)


class RemindersView(QWidget):
    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        title = make_title("fa5s.bell", "Lembretes")
        self.add_btn = QPushButton(" Novo lembrete")
        self.add_btn.setObjectName("refreshBtn")
        self.add_btn.setIcon(qta.icon("fa5s.plus", color="#ffffff"))
        self.add_btn.setIconSize(QSize(15, 15))
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self._add_reminder)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.add_btn)
        root.addLayout(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setObjectName("scrollArea")
        self.list_host = QWidget()
        self.list_layout = QVBoxLayout(self.list_host)
        self.list_layout.setContentsMargins(0, 0, 6, 6)
        self.list_layout.setSpacing(10)
        self.list_layout.addStretch()
        self.scroll.setWidget(self.list_host)
        root.addWidget(self.scroll, 1)

        self.refresh()

    def refresh(self):
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        ordered = sorted(
            self.manager.reminders,
            key=lambda r: (r.enabled, r.next_trigger or "9999-12-31"),
            reverse=True,
        )
        ordered.sort(key=lambda r: r.next_trigger or "9999-12-31")
        for reminder in ordered:
            card = ReminderCard(reminder)
            card.edit_requested.connect(self._edit_reminder)
            card.delete_requested.connect(self._delete_reminder)
            card.toggle_requested.connect(self._toggle_reminder)
            self.list_layout.insertWidget(self.list_layout.count() - 1, card)

        if not self.manager.reminders:
            empty = QLabel("Nenhum lembrete criado ainda.\nClique em \"+ Novo lembrete\" para começar.")
            empty.setObjectName("errorLabel")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.list_layout.insertWidget(0, empty)

    def _add_reminder(self):
        dialog = ReminderDialog(self.manager, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.result_data()
            self.manager.add(**data)
            self.refresh()

    def _edit_reminder(self, reminder_id):
        reminder = next((r for r in self.manager.reminders if r.id == reminder_id), None)
        if reminder is None:
            return
        dialog = ReminderDialog(self.manager, reminder=reminder, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.result_data()
            reminder.title = data["title"]
            reminder.description = data["description"]
            reminder.trigger_type = data["trigger_type"]
            reminder.time = data["time"]
            reminder.date = data["date"]
            reminder.weekdays = data["weekdays"]
            reminder.day_of_month = data["day_of_month"]
            reminder.enabled = data["enabled"]
            self.manager.update(reminder)
            self.refresh()

    def _delete_reminder(self, reminder_id):
        reminder = next((r for r in self.manager.reminders if r.id == reminder_id), None)
        if reminder is None:
            return
        answer = QMessageBox.question(
            self,
            "Excluir lembrete",
            f"Excluir \"{reminder.title}\"?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.manager.remove(reminder_id)
            self.refresh()

    def _toggle_reminder(self, reminder_id):
        self.manager.toggle(reminder_id)
        self.refresh()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Organizador Pessoal")
        self.resize(1100, 760)

        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = QListWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setIconSize(QSize(22, 22))
        self.sidebar.setToolTip("Navegação")
        self._sidebar_entries = (
            ("Notícias", "fa5s.newspaper", True),
            ("Lembretes", "fa5s.bell", True),
            ("Clima", "fa5s.cloud-sun", True),
            ("Tarefas", "fa5s.tasks", False),
            ("Agenda", "fa5s.calendar-alt", False),
            ("Notas", "fa5s.sticky-note", False),
        )
        for name, icon_name, enabled in self._sidebar_entries:
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 46))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setToolTip(name)
            item.setIcon(qta.icon(icon_name, color=ACCENT if enabled else SIDEBAR_DISABLED))
            if not enabled:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            self.sidebar.addItem(item)
        self.sidebar.setCurrentRow(0)
        self.sidebar.currentRowChanged.connect(self._switch_view)

        self.theme_btn = QToolButton()
        self.theme_btn.setObjectName("themeBtn")
        self.theme_btn.setIconSize(QSize(20, 20))
        self.theme_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_btn.clicked.connect(self._toggle_theme)
        self._update_theme_btn()

        sidebar_container = QWidget()
        sidebar_container.setFixedWidth(64)
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        sidebar_layout.addWidget(self.sidebar)
        sidebar_layout.addStretch()
        sidebar_layout.addWidget(self.theme_btn)
        make_shadow(self.sidebar, x=3, y=0, blur=14)

        self.stack = QWidget()
        self.stack_layout = QVBoxLayout(self.stack)
        self.stack_layout.setContentsMargins(24, 20, 24, 20)

        self.reminder_manager = rem.ReminderManager()
        self.news_view = NewsView()
        self.reminders_view = RemindersView(self.reminder_manager)
        self.weather_view = WeatherView()
        self.stack_layout.addWidget(self.news_view)
        self.stack_layout.addWidget(self.reminders_view)
        self.stack_layout.addWidget(self.weather_view)
        self.reminders_view.hide()
        self.weather_view.hide()

        root.addWidget(sidebar_container)
        root.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        self._setup_tray()
        self._setup_scheduler()

    def _update_theme_btn(self):
        if CURRENT_THEME == "dark":
            self.theme_btn.setIcon(qta.icon("fa5s.sun", color=ACCENT_HOVER))
            self.theme_btn.setToolTip("Mudar para tema claro")
        else:
            self.theme_btn.setIcon(qta.icon("fa5s.moon", color=ACCENT))
            self.theme_btn.setToolTip("Mudar para tema escuro")

    def _apply_sidebar_icons(self):
        for item, (_, icon_name, enabled) in zip(
            (self.sidebar.item(i) for i in range(self.sidebar.count())),
            self._sidebar_entries,
        ):
            item.setIcon(qta.icon(icon_name, color=ACCENT if enabled else SIDEBAR_DISABLED))

    def _toggle_theme(self):
        new_theme = "light" if CURRENT_THEME == "dark" else "dark"
        app = QApplication.instance()
        apply_theme(app, new_theme)
        self._update_theme_btn()
        self._apply_sidebar_icons()
        self.reminders_view.refresh()
        QSettings("OrganizadorPessoal", "LifeDashboard").setValue("theme", new_theme)
        if self._tray is not None:
            self._update_tray_icon()

    def _setup_tray(self):
        self._tray = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self._tray = QSystemTrayIcon(QIcon(self._tray_pixmap()), self)
            self._tray.setToolTip("Organizador Pessoal")
            self._tray.show()

    def _update_tray_icon(self):
        if self._tray is not None:
            self._tray.setIcon(QIcon(self._tray_pixmap()))

    def _tray_pixmap(self):
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(ACCENT))
        painter.drawEllipse(8, 8, 48, 48)
        painter.end()
        return pixmap

    def _setup_scheduler(self):
        self._alarm_timer = QTimer(self)
        self._alarm_timer.setInterval(15000)
        self._alarm_timer.timeout.connect(self._check_alarms)
        self._alarm_timer.start()

    def _check_alarms(self):
        fired = self.reminder_manager.check_due()
        if not fired:
            return
        lines = [f"⏰ {r.title}" for r in fired]
        message = "\n".join(lines)
        QApplication.beep()
        if self._tray is not None:
            self._tray.showMessage("Lembrete", message, QSystemTrayIcon.MessageIcon.Information, 10000)
        QMessageBox.information(self, "Lembretes", message)
        self.reminders_view.refresh()

    def closeEvent(self, event):
        self._alarm_timer.stop()
        self.news_view.shutdown()
        self.weather_view.shutdown()
        super().closeEvent(event)

    def _switch_view(self, row):
        self.news_view.setVisible(row == 0)
        self.reminders_view.setVisible(row == 1)
        self.weather_view.setVisible(row == 2)


def apply_stylesheet(app):
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(BG))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Base, QColor(INPUT))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(CARD))
    palette.setColor(QPalette.ColorRole.Text, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Button, QColor(BTN))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(ACCENT))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(SURFACE))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(PLACEHOLDER))
    palette.setColor(QPalette.ColorRole.Link, QColor(ACCENT))
    app.setPalette(palette)
    app.setStyleSheet(f"""
        * {{
            font-family: "Segoe UI";
            outline: none;
        }}
        QMainWindow, QDialog, QMessageBox {{
            background: {BG};
        }}
        QToolTip {{
            background: {SURFACE};
            color: {TEXT};
            border: 1px solid {BORDER};
            border-radius: 6px;
            padding: 6px 10px;
        }}

        #sidebar {{
            background: {SURFACE};
            border: none;
            font-size: 14px;
        }}
        #sidebar::item {{
            margin: 4px 10px;
            padding: 10px 0;
            border-radius: 10px;
        }}
        #sidebar::item:selected {{
            background: {SIDEBAR_SELECTED};
        }}
        #sidebar::item:hover {{
            background: {SIDEBAR_HOVER};
        }}
        #sidebar::item:disabled {{
            color: {SIDEBAR_DISABLED};
        }}

        #themeBtn {{
            background: transparent;
            border: none;
            border-radius: 10px;
            margin: 4px 10px;
            padding: 8px 0;
        }}
        #themeBtn:hover {{
            background: {SIDEBAR_HOVER};
        }}

        #pageTitle {{
            font-size: 20px;
            font-weight: 700;
            color: {TEXT};
        }}
        #status {{
            color: {MUTED};
            font-size: 12px;
        }}

        QPushButton {{
            background: {BTN};
            color: {TEXT};
            border: 1px solid {BORDER};
            border-top: 1px solid {BEVEL_LIGHT};
            border-bottom: 2px solid {BEVEL_DARK};
            border-radius: 8px;
            padding: 7px 14px;
            font-size: 13px;
            font-weight: 600;
        }}
        QPushButton:hover {{ background: {BTN_HOVER}; }}
        QPushButton:pressed {{
            background: {BTN_PRESSED};
            border-top: 2px solid {BEVEL_DARK};
            border-bottom: 1px solid {BEVEL_LIGHT};
        }}
        QPushButton:disabled {{ background: {BTN_DISABLED}; color: {BTN_DISABLED_TEXT}; border-color: {BORDER}; }}

        #refreshBtn {{
            background: {ACCENT};
            color: #ffffff;
            border: none;
            border-bottom: 2px solid {ACCENT_DARK};
        }}
        #refreshBtn:hover {{ background: {ACCENT_HOVER}; }}
        #refreshBtn:pressed {{
            border-top: 2px solid {ACCENT_DARK};
            border-bottom: none;
        }}
        #refreshBtn:disabled {{ background: {BTN_DISABLED}; color: {BTN_DISABLED_TEXT}; }}

        #toggleBtn {{
            background: {TOGGLE_BTN};
            color: {ACCENT};
            border: none;
            padding: 6px 12px;
            font-size: 12px;
        }}
        #toggleBtn:hover {{ background: {TOGGLE_BTN_HOVER}; }}
        #secondaryBtn {{
            background: {SECONDARY_BTN};
            color: {TEXT};
            border: none;
            padding: 6px 12px;
            font-size: 12px;
        }}
        #secondaryBtn:hover {{ background: {SECONDARY_BTN_HOVER}; }}
        #dangerBtn {{
            background: {DANGER_SOFT};
            color: {DANGER};
            border: none;
            padding: 6px 12px;
            font-size: 12px;
        }}
        #dangerBtn:hover {{ background: {DANGER_HOVER}; }}

        #scrollArea {{
            border: none;
            background: transparent;
        }}
        QScrollArea > QWidget > QWidget {{
            background: transparent;
        }}
        QScrollBar:vertical {{
            background: transparent;
            width: 10px;
            margin: 2px;
        }}
        QScrollBar::handle:vertical {{
            background: {SCROLL_HANDLE};
            border-radius: 4px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{ background: {SCROLL_HANDLE_HOVER}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: transparent;
        }}

        #newsCard, #reminderCard {{
            background: {CARD};
            border: 1px solid {BORDER};
            border-radius: 12px;
        }}
        #weatherCard, #dayCard {{
            background: {CARD};
            border: 1px solid {BORDER};
            border-radius: 12px;
        }}
        #clockTime {{
            font-size: 52px;
            font-weight: 700;
            color: {TEXT};
            letter-spacing: 2px;
        }}
        #clockDate {{
            font-size: 16px;
            color: {MUTED};
        }}
        #weatherTemp {{
            font-size: 44px;
            font-weight: 700;
            color: {TEXT};
        }}
        #weatherDesc {{
            font-size: 17px;
            font-weight: 600;
            color: {TEXT};
        }}
        #weatherMeta {{
            font-size: 13px;
            color: {MUTED};
        }}
        #dayCardDay {{
            font-size: 13px;
            font-weight: 700;
            color: {ACCENT};
            text-transform: uppercase;
        }}
        #dayCardDate {{
            font-size: 11px;
            color: {MUTED};
        }}
        #dayCardTemp {{
            font-size: 15px;
            font-weight: 700;
            color: {TEXT};
        }}
        #dayCardPrecip {{
            font-size: 11px;
            color: {MUTED};
        }}
        #newsCard:hover {{
            border: 1px solid {BORDER_HOVER};
            background: {CARD_HOVER};
        }}
        #reminderCard[paused="true"] {{
            background: {PAUSED_BG};
            border: 1px solid {PAUSED_BORDER};
        }}
        #newsThumb {{
            background: {THUMB_BG};
            border-radius: 10px;
        }}
        #newsCategory {{
            color: {ACCENT};
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
        }}
        #newsDate {{
            color: {MUTED};
            font-size: 12px;
        }}
        #newsSource {{
            color: {MUTED};
            font-size: 11px;
            font-weight: 600;
            background: {BTN};
            border: 1px solid {BORDER};
            border-radius: 6px;
            padding: 1px 8px;
        }}
        #newsTitle {{
            font-size: 15px;
            font-weight: 600;
            color: {TEXT};
        }}
        #errorLabel {{
            color: {DANGER};
            font-size: 14px;
            padding: 30px;
            background: {CARD};
            border: 1px solid {DANGER_SOFT};
            border-radius: 12px;
        }}
        #reminderIcon {{
            font-size: 24px;
            min-width: 40px;
        }}
        #reminderTitle {{
            font-size: 15px;
            font-weight: 700;
            color: {TEXT};
        }}
        #reminderDesc {{
            font-size: 13px;
            color: {MUTED};
        }}
        #reminderSchedule {{
            font-size: 12px;
            font-weight: 700;
            color: {ACCENT};
        }}
        #reminderNext {{
            font-size: 12px;
            color: {MUTED};
        }}

        QLineEdit, QTimeEdit, QDateEdit, QSpinBox, QComboBox {{
            padding: 8px 10px;
            border: 1px solid {BORDER};
            border-radius: 8px;
            background: {INPUT};
            color: {TEXT};
            font-size: 13px;
            selection-background-color: {ACCENT};
        }}
        QLineEdit:focus, QTimeEdit:focus, QDateEdit:focus, QSpinBox:focus, QComboBox:focus {{
            border: 1px solid {ACCENT};
        }}
        QLineEdit::placeholder {{ color: {PLACEHOLDER}; }}
        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}
        QComboBox QAbstractItemView {{
            background: {SURFACE};
            color: {TEXT};
            border: 1px solid {BORDER};
            border-radius: 8px;
            selection-background-color: {SIDEBAR_SELECTED};
            padding: 4px;
        }}
        QCheckBox {{
            color: {TEXT};
            font-size: 13px;
            spacing: 8px;
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {BORDER};
            border-radius: 4px;
            background: {INPUT};
        }}
        QCheckBox::indicator:checked {{
            background: {ACCENT};
            border-color: {ACCENT};
        }}
        QTimeEdit::up-button, QTimeEdit::down-button,
        QSpinBox::up-button, QSpinBox::down-button,
        QDateEdit::up-button, QDateEdit::down-button {{
            background: transparent;
            border: none;
            width: 16px;
        }}
        QCalendarWidget QWidget {{
            background: {SURFACE};
            color: {TEXT};
        }}
        QCalendarWidget QAbstractItemView {{
            background: {SURFACE};
            color: {TEXT};
            selection-background-color: {ACCENT};
            selection-color: #ffffff;
        }}
        QCalendarWidget QToolButton {{
            background: transparent;
            border: none;
            border-radius: 6px;
            color: {TEXT};
            padding: 4px 8px;
        }}
        QDialogButtonBox QPushButton {{
            min-width: 84px;
        }}
        QMessageBox QLabel {{
            color: {TEXT};
        }}
    """)
    apply_shadow_colors(app)


def main():
    app = QApplication(sys.argv)
    saved_theme = QSettings("OrganizadorPessoal", "LifeDashboard").value("theme", "dark")
    apply_theme(app, saved_theme)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
