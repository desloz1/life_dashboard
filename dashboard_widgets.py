"""Widgets do Início (dashboard): cards de resumo, linhas de notícia e gráfico."""

import datetime

import qtawesome as qta
from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import common
import news
import theme


class SummaryCard(QFrame):
    clicked = Signal()

    def __init__(self, icon_name, icon_color, title, parent=None):
        super().__init__(parent)
        self.setObjectName("dashCard")
        common.make_shadow(self, y=3, blur=16)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        top = QHBoxLayout()
        self.icon_label = QLabel()
        self.set_icon(icon_name, icon_color)
        top.addWidget(self.icon_label)
        title_label = QLabel(title)
        title_label.setObjectName("dashCardTitle")
        top.addWidget(title_label)
        top.addStretch()
        arrow = QLabel("→")
        arrow.setObjectName("dashLink")
        top.addWidget(arrow)
        layout.addLayout(top)

        self.value = QLabel("—")
        self.value.setObjectName("dashCardValue")
        self.value.setWordWrap(True)
        layout.addWidget(self.value)

        self.sub = QLabel("")
        self.sub.setObjectName("dashCardSub")
        self.sub.setWordWrap(True)
        layout.addWidget(self.sub)
        layout.addStretch()

    def set_icon(self, icon_name, color):
        self.icon_label.setPixmap(qta.icon(icon_name, color=color).pixmap(22, 22))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class DashNewsRow(QFrame):
    clicked = Signal(str)

    def __init__(self, item, parent=None):
        super().__init__(parent)
        self._url = item["url"]
        self.setObjectName("dashNewsRow")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(10)

        bullet = QLabel("•")
        bullet.setObjectName("dashNewsBullet")
        layout.addWidget(bullet)

        self.title = QLabel(item["title"])
        self.title.setObjectName("dashNewsTitle")
        self.title.setWordWrap(True)
        self.title.setMaximumHeight(40)
        layout.addWidget(self.title, 1)

        meta = QHBoxLayout()
        meta.setSpacing(6)
        source = QLabel(item.get("source") or "")
        source.setObjectName("newsSource")
        meta.addWidget(source)
        rel = news._relative_time(item.get("date"))
        if rel:
            time_label = QLabel(rel)
            time_label.setObjectName("newsTime")
            meta.addWidget(time_label)
        layout.addLayout(meta)

    def set_seen(self, seen):
        self.setProperty("seen", "true" if seen else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._url)
        super().mouseReleaseEvent(event)


class TaskWeekChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(120)
        self.setMinimumWidth(220)
        self._days = []

    def set_data(self, days):
        self._days = days
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self._days:
            painter.setPen(QColor(theme.MUTED))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Sem dados")
            return
        today = datetime.date.today()
        if sum(count for _, count in self._days) == 0:
            painter.setPen(QColor(theme.MUTED))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Sem conclusões ainda")
            return
        max_count = max((count for _, count in self._days), default=0) or 1
        n = len(self._days)
        slot = self.width() / n
        bar_w = min(34.0, slot * 0.55)
        baseline = self.height() - 22
        label_font = painter.font()
        label_font.setPointSizeF(max(7, 8 * theme.FONT_SCALE))
        painter.setPen(QColor(theme.BORDER))
        painter.drawLine(4, baseline, self.width() - 4, baseline)
        for i, (date, count) in enumerate(self._days):
            cx = slot * i + slot / 2
            if count:
                bh = max(3, int((count / max_count) * (baseline - 18)))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(theme.ACCENT_HOVER if date == today else theme.ACCENT))
                painter.drawRoundedRect(QRectF(cx - bar_w / 2, baseline - bh, bar_w, bh), 3, 3)
                painter.setPen(QColor(theme.TEXT))
                painter.setFont(label_font)
                painter.drawText(
                    QRectF(cx - slot / 2, baseline - bh - 16, slot, 14),
                    Qt.AlignmentFlag.AlignHCenter, str(count))
            painter.setPen(QColor(theme.ACCENT if date == today else theme.MUTED))
            painter.setFont(label_font)
            painter.drawText(
                QRectF(cx - slot / 2, baseline + 2, slot, 14),
                Qt.AlignmentFlag.AlignHCenter, str(date.day))


class DashTodayBox(QFrame):
    """Bloco "Dia de hoje": clima atual, tarefas/lembretes do dia, feriado e webcams."""

    cameras_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dashToday")
        common.make_shadow(self, y=3, blur=16)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 12)
        root.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(8)
        icon = QLabel()
        icon.setPixmap(qta.icon("fa5s.calendar-day", color=theme.ACCENT).pixmap(18, 18))
        header.addWidget(icon)
        title = QLabel("Dia de hoje")
        title.setObjectName("dashTodayTitle")
        header.addWidget(title)
        header.addStretch()
        self.cam_btn = QPushButton(" Ver câmeras")
        self.cam_btn.setObjectName("secondaryBtn")
        self.cam_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cam_btn.clicked.connect(self.cameras_clicked.emit)
        header.addWidget(self.cam_btn)
        root.addLayout(header)

        row = QHBoxLayout()
        row.setSpacing(24)

        weather_col = QVBoxLayout()
        weather_col.setSpacing(2)
        weather_top = QHBoxLayout()
        weather_top.setSpacing(8)
        self.weather_icon = QLabel()
        self.weather_icon.setObjectName("dashTodayIcon")
        weather_top.addWidget(self.weather_icon)
        self.weather_temp = QLabel("—")
        self.weather_temp.setObjectName("dashTodayTemp")
        weather_top.addWidget(self.weather_temp)
        weather_top.addStretch()
        weather_col.addLayout(weather_top)
        self.weather_desc = QLabel("")
        self.weather_desc.setObjectName("dashTodaySub")
        weather_col.addWidget(self.weather_desc)
        self.weather_range = QLabel("")
        self.weather_range.setObjectName("dashTodaySub")
        weather_col.addWidget(self.weather_range)
        row.addLayout(weather_col, 1)

        items_col = QVBoxLayout()
        items_col.setSpacing(3)
        self.tasks_label = QLabel("")
        self.tasks_label.setObjectName("dashTodayItem")
        items_col.addWidget(self.tasks_label)
        self.reminders_label = QLabel("")
        self.reminders_label.setObjectName("dashTodayItem")
        items_col.addWidget(self.reminders_label)
        self.holiday_label = QLabel("")
        self.holiday_label.setObjectName("dashTodayItem")
        items_col.addWidget(self.holiday_label)
        self.cameras_label = QLabel("")
        self.cameras_label.setObjectName("dashTodayItem")
        items_col.addWidget(self.cameras_label)
        items_col.addStretch()
        row.addLayout(items_col, 2)

        root.addLayout(row)

    def set_weather(self, icon_name, color, temp, desc, max_temp, min_temp):
        self.weather_icon.setPixmap(qta.icon(icon_name, color=color).pixmap(26, 26))
        self.weather_temp.setText(f"{temp}°C")
        self.weather_desc.setText(desc)
        self.weather_range.setText(f"máx {max_temp}° · mín {min_temp}°")

    def set_weather_loading(self):
        self.weather_icon.clear()
        self.weather_temp.setText("—")
        self.weather_desc.setText("Clima: carregando…")
        self.weather_range.setText("")

    def set_items(self, n_tasks, n_reminders, holiday=None, n_cameras=0):
        self.tasks_label.setText(
            f"{n_tasks} tarefa{'s' if n_tasks != 1 else ''} para hoje"
            if n_tasks else "Nenhuma tarefa para hoje"
        )
        self.reminders_label.setText(
            f"{n_reminders} lembrete{'s' if n_reminders != 1 else ''} hoje"
            if n_reminders else "Sem lembretes para hoje"
        )
        if holiday:
            self.holiday_label.setText(f"★ Feriado: {holiday}")
            self.holiday_label.setVisible(True)
        else:
            self.holiday_label.clear()
            self.holiday_label.setVisible(False)
        self.cameras_label.setText(
            f"Câmeras de Blumenau: {n_cameras}"
            if n_cameras else "Webcams indisponíveis"
        )