import datetime

import qtawesome as qta
import requests
from PySide6.QtCore import QPointF, QSize, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

import common
import theme
import weather

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


class TempChart(QFrame):
    def __init__(self, days, parent=None):
        super().__init__(parent)
        self._days = days
        self.setObjectName("weatherCard")
        common.make_shadow(self, y=3, blur=16)
        self.setMinimumHeight(180)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        days = self._days
        if not days:
            painter.end()
            return

        rect = self.rect()
        left, right = 30, rect.width() - 10
        top, bottom = 18, rect.height() - 26

        values_max = [day["max"] for day in days]
        values_min = [day["min"] for day in days]
        v_max = max(values_max + values_min) + 1.0
        v_min = min(values_max + values_min) - 1.0
        span = (v_max - v_min) or 1.0

        def point_x(index):
            return left + (right - left) * index / (len(days) - 1)

        def point_y(value):
            return bottom - (bottom - top) * (value - v_min) / span

        fill = QPainterPath()
        fill.moveTo(point_x(0), bottom)
        for index in range(len(days)):
            fill.lineTo(point_x(index), point_y(values_max[index]))
        fill.lineTo(point_x(len(days) - 1), bottom)
        fill.closeSubpath()
        fill_color = QColor(theme.ACCENT)
        fill_color.setAlpha(45)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.fillPath(fill, fill_color)

        path_max = QPainterPath()
        path_min = QPainterPath()
        for index in range(len(days)):
            p_max = QPointF(point_x(index), point_y(values_max[index]))
            p_min = QPointF(point_x(index), point_y(values_min[index]))
            if index == 0:
                path_max.moveTo(p_max)
                path_min.moveTo(p_min)
            else:
                path_max.lineTo(p_max)
                path_min.lineTo(p_min)

        painter.setPen(QPen(QColor(theme.MUTED), 2))
        painter.drawPath(path_min)
        painter.setPen(QPen(QColor(theme.ACCENT), 2))
        painter.drawPath(path_max)

        font_metrics = painter.fontMetrics()

        painter.setPen(Qt.PenStyle.NoPen)
        for index in range(len(days)):
            painter.setBrush(QColor(theme.ACCENT))
            painter.drawEllipse(QPointF(point_x(index), point_y(values_max[index])), 3.5, 3.5)
            painter.setBrush(QColor(theme.MUTED))
            painter.drawEllipse(QPointF(point_x(index), point_y(values_min[index])), 3.0, 3.0)

        painter.setPen(QColor(theme.ACCENT))
        for index in range(len(days)):
            text = f"{values_max[index]}°"
            painter.drawText(
                QPointF(point_x(index) - font_metrics.horizontalAdvance(text) / 2, point_y(values_max[index]) - 7),
                text,
            )
        painter.setPen(QColor(theme.MUTED))
        for index in range(len(days)):
            text = f"{values_min[index]}°"
            label_y = min(point_y(values_min[index]) + font_metrics.height() + 2, bottom + 12)
            painter.drawText(
                QPointF(point_x(index) - font_metrics.horizontalAdvance(text) / 2, label_y),
                text,
            )

        painter.setPen(QColor(theme.MUTED))
        for index, day in enumerate(days):
            date = datetime.date.fromisoformat(day["date"])
            label = f"{WEEKDAYS_SHORT[date.weekday()]} {date.strftime('%d/%m')}"
            painter.drawText(
                QPointF(point_x(index) - font_metrics.horizontalAdvance(label) / 2, bottom + 18),
                label,
            )

        swatch = 16
        painter.setPen(QPen(QColor(theme.ACCENT), 2))
        painter.drawLine(left, 10, left + swatch, 10)
        painter.setPen(QColor(theme.MUTED))
        painter.drawText(left + swatch + 6, 14, "Máx")
        painter.setPen(QPen(QColor(theme.MUTED), 2))
        painter.drawLine(left + 66, 10, left + 66 + swatch, 10)
        painter.drawText(left + 66 + swatch + 6, 14, "Mín")
        painter.end()


class WeatherView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)

        header = QHBoxLayout()
        header.addWidget(common.make_title("fa5s.cloud-sun", "Clima · Blumenau"))
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
        common.make_shadow(self.clock_card, y=3, blur=16)
        clock_layout = QVBoxLayout(self.clock_card)
        clock_layout.setContentsMargins(24, 14, 24, 14)
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

        self.page_scroll = QScrollArea()
        self.page_scroll.setWidgetResizable(True)
        self.page_scroll.setObjectName("scrollArea")
        self.page_host = QWidget()
        self.page_layout = QVBoxLayout(self.page_host)
        self.page_layout.setContentsMargins(0, 0, 6, 6)
        self.page_layout.setSpacing(16)
        self.page_scroll.setWidget(self.page_host)
        root.addWidget(self.page_scroll, 1)

        self.current_card = QFrame()
        self.current_card.setObjectName("weatherCard")
        common.make_shadow(self.current_card, y=3, blur=16)
        self.current_layout = QVBoxLayout(self.current_card)
        self.current_layout.setContentsMargins(24, 20, 24, 20)
        self.page_layout.addWidget(self.current_card)

        self.hourly_scroll = self._make_h_scroll(112, "hourScroll")
        self.page_layout.addWidget(self._section_title("Próximas 24 horas"))
        self.page_layout.addWidget(self.hourly_scroll)

        self.forecast_scroll = self._make_h_scroll(200, "scrollArea")
        self.page_layout.addWidget(self._section_title("Próximos 7 dias"))
        self.page_layout.addWidget(self.forecast_scroll)

        self.page_layout.addWidget(self._section_title("Tendência de temperatura"))
        self.chart = TempChart([])
        self.page_layout.addWidget(self.chart)

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

    def _make_h_scroll(self, height, object_name):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName(object_name)
        scroll.setFixedHeight(height)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        host = QWidget()
        row = QHBoxLayout(host)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        scroll.setWidget(host)
        return scroll

    def _section_title(self, text):
        label = QLabel(text)
        label.setObjectName("pageTitle")
        label.setContentsMargins(0, 4, 0, 0)
        return label

    def _update_clock(self):
        now = datetime.datetime.now()
        self.time_label.setText(now.strftime("%H:%M:%S"))
        self.date_label.setText(format_full_date(now.date()))

    def load_weather(self):
        if self._worker and self._worker.isRunning():
            return
        self.status.setText("Carregando…")
        self.refresh_btn.setEnabled(False)
        self._clear_content()

        sk = common.SkeletonShimmer()
        sk.setObjectName("weatherCard")
        sk.setFixedHeight(130)
        self.current_layout.addWidget(sk)

        hourly_row = self.hourly_scroll.widget().layout()
        for _ in range(6):
            hsk = common.SkeletonShimmer()
            hsk.setFixedSize(72, 104)
            hourly_row.addWidget(hsk)
        hourly_row.addStretch()

        forecast_row = self.forecast_scroll.widget().layout()
        for _ in range(4):
            dsk = common.SkeletonShimmer()
            dsk.setObjectName("dayCard")
            dsk.setFixedSize(120, 180)
            forecast_row.addWidget(dsk)
        forecast_row.addStretch()

        chart_sk = common.SkeletonShimmer()
        chart_sk.setObjectName("weatherCard")
        chart_sk.setFixedHeight(180)
        self.page_layout.addWidget(chart_sk)

        self._worker = WeatherWorker(self)
        self._worker.finished_ok.connect(self._on_loaded)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _clear_content(self):
        while self.current_layout.count():
            item = self.current_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        for scroll in (self.hourly_scroll, self.forecast_scroll):
            row = scroll.widget().layout()
            while row.count():
                item = row.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
        self.chart._days = []
        self.chart.update()

    def _on_loaded(self, data):
        common.remove_shimmers(self.current_layout)
        common.remove_shimmers(self.hourly_scroll.widget().layout())
        common.remove_shimmers(self.forecast_scroll.widget().layout())
        common.remove_shimmers(self.page_layout)

        current = QWidget()
        row = QHBoxLayout(current)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(20)

        icon_label = QLabel()
        icon_label.setPixmap(qta.icon(data["icon"], color=data["color"]).pixmap(64, 64))
        row.addWidget(icon_label)

        summary = QVBoxLayout()
        summary.setSpacing(4)
        temp = QLabel(f"{data['temperature']}°C")
        temp.setObjectName("weatherTemp")
        summary.addWidget(temp)
        desc = QLabel(data["description"])
        desc.setObjectName("weatherDesc")
        summary.addWidget(desc)
        summary.addStretch()
        row.addLayout(summary)
        row.addStretch()

        metrics = [
            (f"{data['feels_like']}°", "Sensação"),
            (f"{data['humidity']}%", "Umidade"),
            (f"{data['wind']} km/h", "Vento"),
            (f"{data['pressure']} hPa", "Pressão"),
            (f"{data['max']}° / {data['min']}°", "Máx / Mín"),
            (f"{data['precip']} mm", "Chuva"),
            (data["sunrise"], "Nascer do sol"),
            (data["sunset"], "Pôr do sol"),
        ]
        grid = QGridLayout()
        grid.setSpacing(8)
        for index, (value, label) in enumerate(metrics):
            grid.addWidget(self._metric_chip(value, label), index // 4, index % 4)
        row.addLayout(grid)

        self.current_layout.addWidget(current)

        hourly_row = self.hourly_scroll.widget().layout()
        for index, hour in enumerate(data["hours"]):
            hourly_row.addWidget(self._build_hour_card(hour, index))
        hourly_row.addStretch()

        forecast_row = self.forecast_scroll.widget().layout()
        for day in data["days"]:
            forecast_row.addWidget(self._build_day_card(day))
        forecast_row.addStretch()

        self.chart._days = data["days"]
        self.chart.update()

        self.status.setText("Atualizado agora")

    def _metric_chip(self, value, label):
        chip = QFrame()
        chip.setObjectName("metricChip")
        layout = QVBoxLayout(chip)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label = QLabel(value)
        value_label.setObjectName("metricValue")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(value_label)
        label_label = QLabel(label)
        label_label.setObjectName("metricLabel")
        label_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label_label)
        return chip

    def _build_hour_card(self, hour, index):
        card = QFrame()
        card.setObjectName("hourCard")
        card.setFixedSize(72, 104)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        try:
            hour_time = datetime.datetime.fromisoformat(hour["time"])
            hour_text = "agora" if index == 0 else hour_time.strftime("%Hh")
        except ValueError:
            hour_text = hour["time"][-5:]
        hour_label = QLabel(hour_text)
        hour_label.setObjectName("hourLabel")
        hour_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hour_label)

        icon_label = QLabel()
        icon_label.setPixmap(qta.icon(hour["icon"], color=hour["color"]).pixmap(26, 26))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        temp = QLabel(f"{hour['temp']}°")
        temp.setObjectName("hourTemp")
        temp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(temp)
        return card

    def _build_day_card(self, day):
        date = datetime.date.fromisoformat(day["date"])
        card = QFrame()
        card.setObjectName("dayCard")
        common.make_shadow(card, y=3, blur=14)
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
        common.remove_shimmers(self.current_layout)
        common.remove_shimmers(self.hourly_scroll.widget().layout())
        common.remove_shimmers(self.forecast_scroll.widget().layout())
        common.remove_shimmers(self.page_layout)
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
