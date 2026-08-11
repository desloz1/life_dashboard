import datetime

import qtawesome as qta
from PySide6.QtCore import QRectF, QSize, Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

import common
import log
import news
import reminders as rem
import scraper
import theme
from weather_ui import WeatherWorker, format_full_date

logger = log.get_logger("life_dashboard.dashboard")


def greeting():
    hour = datetime.datetime.now().hour
    if hour < 5:
        return "Boa madrugada 🌙"
    if hour < 12:
        return "Bom dia ☀️"
    if hour < 18:
        return "Boa tarde ⛅"
    return "Boa noite 🌙"


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


class DashNewsWorker(QThread):
    finished_ok = Signal(list)
    failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        raw = []
        errors = []
        for source in scraper.SOURCES:
            if self.isInterruptionRequested():
                return
            try:
                raw.extend(scraper.fetch_news(source, limit=10))
            except Exception as exc:
                errors.append(f"{source}: {exc}")
                logger.warning("Falha ao buscar notícias de %s: %s", source, exc)
        if not raw:
            self.failed.emit("; ".join(errors) or "Nenhuma notícia carregada")
            return
        items = news.sort_by_date(raw, limit=10)
        if not self.isInterruptionRequested():
            self.finished_ok.emit(items)


class DashTechWorker(QThread):
    finished_ok = Signal(list)
    failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        try:
            raw = scraper.fetch_tech_news(limit=15)
        except Exception as exc:
            logger.warning("Falha ao buscar notícias de tecnologia: %s", exc)
            if not self.isInterruptionRequested():
                self.failed.emit(str(exc))
            return
        items = news.sort_by_date(raw, limit=10)
        if not self.isInterruptionRequested():
            self.finished_ok.emit(items)


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


class DashboardView(QWidget):
    open_news = Signal()
    open_reminders = Signal()
    open_weather = Signal()
    open_tasks = Signal()
    open_agenda = Signal()
    new_task_requested = Signal()
    new_reminder_requested = Signal()

    def __init__(self, reminder_manager, tasks_manager, parent=None):
        super().__init__(parent)
        self.reminder_manager = reminder_manager
        self.tasks_manager = tasks_manager
        self._weather_worker = None
        self._news_worker = None
        self._news_items = []
        self._tech_worker = None
        self._tech_items = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(12)
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        self.greeting_label = QLabel("")
        self.greeting_label.setObjectName("dashGreeting")
        text_col.addWidget(self.greeting_label)
        self.date_label = QLabel("")
        self.date_label.setObjectName("dashDate")
        text_col.addWidget(self.date_label)
        header.addLayout(text_col)
        header.addStretch()
        self.refresh_btn = QPushButton(" Atualizar")
        self.refresh_btn.setObjectName("refreshBtn")
        self.refresh_btn.setIcon(qta.icon("fa5s.sync-alt", color="#ffffff"))
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.load_weather)
        header.addWidget(self.refresh_btn)
        root.addLayout(header)

        grid = QGridLayout()
        grid.setSpacing(12)
        self.reminder_card = SummaryCard("fa5s.bell", theme.ACCENT, "Lembretes")
        self.reminder_card.clicked.connect(self.open_reminders.emit)
        self.task_card = SummaryCard("fa5s.tasks", "#34c38f", "Tarefas")
        self.task_card.clicked.connect(self.open_tasks.emit)
        self.weather_card = SummaryCard("fa5s.cloud-sun", theme.ACCENT_HOVER, "Clima agora")
        self.weather_card.clicked.connect(self.open_weather.emit)
        grid.addWidget(self.reminder_card, 0, 0)
        grid.addWidget(self.task_card, 0, 1)
        grid.addWidget(self.weather_card, 0, 2)
        root.addLayout(grid)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        news_btn = QPushButton("Notícias")
        news_btn.setObjectName("dashAction")
        news_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        news_btn.clicked.connect(self.open_news.emit)
        agenda_btn = QPushButton("Agenda")
        agenda_btn.setObjectName("dashAction")
        agenda_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        agenda_btn.clicked.connect(self.open_agenda.emit)
        new_task_btn = QPushButton(" Nova tarefa")
        new_task_btn.setObjectName("dashAction")
        new_task_btn.setIcon(qta.icon("fa5s.plus", color=theme.ACCENT))
        new_task_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_task_btn.clicked.connect(self.new_task_requested.emit)
        new_reminder_btn = QPushButton(" Novo lembrete")
        new_reminder_btn.setObjectName("dashAction")
        new_reminder_btn.setIcon(qta.icon("fa5s.plus", color=theme.ACCENT))
        new_reminder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_reminder_btn.clicked.connect(self.new_reminder_requested.emit)
        actions.addWidget(news_btn)
        actions.addWidget(agenda_btn)
        actions.addWidget(new_task_btn)
        actions.addWidget(new_reminder_btn)
        actions.addStretch()
        root.addLayout(actions)

        stats_header = QHBoxLayout()
        stats_header.setSpacing(8)
        stats_icon = QLabel()
        stats_icon.setPixmap(qta.icon("fa5s.chart-line", color=theme.ACCENT).pixmap(18, 18))
        stats_header.addWidget(stats_icon)
        stats_title = QLabel("Estatísticas de tarefas")
        stats_title.setObjectName("dashStatsTitle")
        stats_header.addWidget(stats_title)
        stats_header.addStretch()
        root.addLayout(stats_header)

        stats_box = QFrame()
        stats_box.setObjectName("dashStats")
        common.make_shadow(stats_box, y=3, blur=16)
        stats_layout = QHBoxLayout(stats_box)
        stats_layout.setContentsMargins(14, 12, 14, 12)
        stats_layout.setSpacing(16)

        self.stats_chart = TaskWeekChart()
        stats_layout.addWidget(self.stats_chart, 2)

        side = QVBoxLayout()
        side.setSpacing(6)

        streak_row = QHBoxLayout()
        streak_row.setSpacing(8)
        streak_icon = QLabel()
        streak_icon.setPixmap(qta.icon("fa5s.fire", color=theme.WARN).pixmap(20, 20))
        streak_row.addWidget(streak_icon)
        self.streak_value = QLabel("0")
        self.streak_value.setObjectName("streakValue")
        streak_row.addWidget(self.streak_value)
        self.streak_label = QLabel("dias de sequência")
        self.streak_label.setObjectName("streakLabel")
        streak_row.addWidget(self.streak_label)
        streak_row.addStretch()
        side.addLayout(streak_row)

        self.week_total = QLabel("")
        self.week_total.setObjectName("weekTotal")
        side.addWidget(self.week_total)

        sep = QFrame()
        sep.setObjectName("sidebarSep")
        sep.setFixedHeight(1)
        side.addWidget(sep)

        self._cat_layout = QVBoxLayout()
        self._cat_layout.setSpacing(5)
        side.addLayout(self._cat_layout)
        side.addStretch()
        stats_layout.addLayout(side, 1)
        root.addWidget(stats_box)

        news_header = QHBoxLayout()
        news_header.setSpacing(8)
        news_icon = QLabel()
        news_icon.setPixmap(qta.icon("fa5s.newspaper", color=theme.ACCENT).pixmap(18, 18))
        news_header.addWidget(news_icon)
        news_title = QLabel("Últimas notícias")
        news_title.setObjectName("dashNewsHeader")
        news_header.addWidget(news_title)
        news_header.addStretch()
        self.news_status = QLabel("")
        self.news_status.setObjectName("status")
        news_header.addWidget(self.news_status)
        self.news_refresh = QPushButton()
        self.news_refresh.setObjectName("cardBtn")
        self.news_refresh.setIcon(qta.icon("fa5s.sync-alt", color=theme.MUTED))
        self.news_refresh.setIconSize(QSize(16, 16))
        self.news_refresh.setFixedSize(30, 30)
        self.news_refresh.setToolTip("Atualizar notícias")
        self.news_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.news_refresh.clicked.connect(self.load_news)
        news_header.addWidget(self.news_refresh)
        root.addLayout(news_header)

        self._news_rows = {}
        self.news_list_host = QWidget()
        self.news_list_layout = QVBoxLayout(self.news_list_host)
        self.news_list_layout.setContentsMargins(0, 0, 4, 0)
        self.news_list_layout.setSpacing(8)
        self.news_scroll = QScrollArea()
        self.news_scroll.setWidgetResizable(True)
        self.news_scroll.setObjectName("scrollArea")
        self.news_scroll.setWidget(self.news_list_host)
        self.news_scroll.setMaximumHeight(320)
        root.addWidget(self.news_scroll)

        tech_header = QHBoxLayout()
        tech_header.setSpacing(8)
        tech_icon = QLabel()
        tech_icon.setPixmap(qta.icon("fa5s.microchip", color=theme.ACCENT).pixmap(18, 18))
        tech_header.addWidget(tech_icon)
        tech_title = QLabel("Tecnologia")
        tech_title.setObjectName("dashNewsHeader")
        tech_header.addWidget(tech_title)
        tech_header.addStretch()
        self.tech_status = QLabel("")
        self.tech_status.setObjectName("status")
        tech_header.addWidget(self.tech_status)
        self.tech_refresh = QPushButton()
        self.tech_refresh.setObjectName("cardBtn")
        self.tech_refresh.setIcon(qta.icon("fa5s.sync-alt", color=theme.MUTED))
        self.tech_refresh.setIconSize(QSize(16, 16))
        self.tech_refresh.setFixedSize(30, 30)
        self.tech_refresh.setToolTip("Atualizar notícias de tecnologia")
        self.tech_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tech_refresh.clicked.connect(self.load_tech_news)
        tech_header.addWidget(self.tech_refresh)
        root.addLayout(tech_header)

        self._tech_rows = {}
        self.tech_list_host = QWidget()
        self.tech_list_layout = QVBoxLayout(self.tech_list_host)
        self.tech_list_layout.setContentsMargins(0, 0, 4, 0)
        self.tech_list_layout.setSpacing(8)
        self.tech_scroll = QScrollArea()
        self.tech_scroll.setWidgetResizable(True)
        self.tech_scroll.setObjectName("scrollArea")
        self.tech_scroll.setWidget(self.tech_list_host)
        self.tech_scroll.setMaximumHeight(320)
        root.addWidget(self.tech_scroll)

        root.addStretch()

        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(1000)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start()

        self._auto_timer = QTimer(self)
        self._auto_timer.setInterval(30 * 60 * 1000)
        self._auto_timer.timeout.connect(self.load_weather)
        self._auto_timer.start()

        self.refresh()
        self.load_weather()
        self.load_news()
        self.load_tech_news()

    def _update_clock(self):
        now = datetime.datetime.now()
        self.greeting_label.setText(f"{greeting()} 👋")
        self.date_label.setText(f"{format_full_date(now.date())} · {now:%H:%M:%S}")

    def refresh(self):
        self._update_clock()
        self._refresh_reminders()
        self._refresh_tasks()
        self._refresh_stats()

    def _refresh_reminders(self):
        now = datetime.datetime.now()
        overdue = [r for r in self.reminder_manager.reminders if rem.is_overdue(r, now)]
        candidates = [
            r for r in self.reminder_manager.reminders
            if r.enabled and r.next_trigger and not rem.is_snoozed(r, now)
            and datetime.datetime.fromisoformat(r.next_trigger) > now
        ]
        candidates.sort(key=lambda r: r.next_trigger)
        next_reminder = candidates[0] if candidates else None

        if overdue:
            count = len(overdue)
            self.reminder_card.value.setText(f"{count} atrasado{'s' if count != 1 else ''}")
            self.reminder_card.sub.setText(
                f"{next_reminder.title} · {rem.format_next(next_reminder.next_trigger)}"
                if next_reminder else "Revise os lembretes atrasados"
            )
        elif next_reminder:
            self.reminder_card.value.setText(next_reminder.title)
            self.reminder_card.sub.setText(f"Próximo: {rem.format_next(next_reminder.next_trigger)}")
        else:
            self.reminder_card.value.setText("Nenhum")
            self.reminder_card.sub.setText("Sem lembretes agendados")

    def _refresh_tasks(self):
        today = datetime.date.today()
        pending = [t for t in self.tasks_manager.tasks if not t.completed]
        late = 0
        next_info = None
        for task in pending:
            if not task.due:
                continue
            try:
                due = datetime.date.fromisoformat(task.due)
            except (ValueError, TypeError):
                continue
            if due < today:
                late += 1
            if next_info is None or due < next_info[1]:
                next_info = (task, due)

        count = len(pending)
        self.task_card.value.setText(f"{count} pendente{'s' if count != 1 else ''}")
        if late:
            self.task_card.sub.setText(
                f"{late} atrasada{'s' if late != 1 else ''} · {next_info[0].title} ({next_info[1]:%d/%m})"
                if next_info else f"{late} atrasada{'s' if late != 1 else ''}"
            )
        elif next_info:
            self.task_card.sub.setText(f"{next_info[0].title} · {next_info[1]:%d/%m/%Y}")
        else:
            self.task_card.sub.setText("Sem tarefas com prazo")

    def _refresh_stats(self):
        week = self.tasks_manager.completed_last_days(7)
        self.stats_chart.set_data(week)
        streak = self.tasks_manager.streak_days()
        self.streak_value.setText(str(streak))
        self.streak_label.setText("dia de sequência" if streak == 1 else "dias de sequência")
        total_week = sum(count for _, count in week)
        self.week_total.setText(
            f"{total_week} concluída{'s' if total_week != 1 else ''} nos últimos 7 dias"
            if total_week else "Nenhuma tarefa concluída nos últimos 7 dias"
        )
        self._render_categories()

    def _render_categories(self):
        while self._cat_layout.count():
            item = self._cat_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        stats = self.tasks_manager.category_stats()
        if not stats:
            empty = QLabel("Sem tarefas criadas ainda.")
            empty.setObjectName("dashStatsEmpty")
            self._cat_layout.addWidget(empty)
            return
        for entry in stats:
            self._cat_layout.addWidget(self._make_cat_row(entry))

    def _make_cat_row(self, entry):
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        name = QLabel(entry["category"])
        name.setObjectName("dashCatName")
        name.setFixedWidth(96)
        lay.addWidget(name)
        bar = QProgressBar()
        bar.setObjectName("catBar")
        bar.setRange(0, 100)
        bar.setValue(entry["pct"])
        bar.setFormat("")
        bar.setFixedHeight(12)
        lay.addWidget(bar, 1)
        pct = QLabel(f"{entry['pct']}% · {entry['done']}/{entry['total']}")
        pct.setObjectName("dashCatPct")
        pct.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        pct.setFixedWidth(72)
        lay.addWidget(pct)
        return row

    def load_weather(self):
        if self._weather_worker and self._weather_worker.isRunning():
            return
        self.weather_card.value.setText("—")
        self.weather_card.sub.setText("Carregando…")
        self._weather_worker = WeatherWorker(self)
        self._weather_worker.finished_ok.connect(self._on_weather_loaded)
        self._weather_worker.failed.connect(self._on_weather_failed)
        self._weather_worker.start()

    def _on_weather_loaded(self, data):
        self.weather_card.set_icon(data["icon"], data["color"])
        self.weather_card.value.setText(f"{data['temperature']}°C")
        self.weather_card.sub.setText(data["description"])
        self.status_ok()

    def _on_weather_failed(self, error):
        self.weather_card.value.setText("—")
        self.weather_card.sub.setText("Sem conexão")

    def status_ok(self):
        pass

    def load_news(self):
        if self._news_worker and self._news_worker.isRunning():
            return
        self.news_status.setText("Carregando…")
        self.news_refresh.setEnabled(False)
        self._clear_news()
        for _ in range(3):
            sk = common.SkeletonShimmer()
            sk.setObjectName("newsCard")
            sk.setFixedHeight(40)
            self.news_list_layout.addWidget(sk)
        self._news_worker = DashNewsWorker(self)
        self._news_worker.finished_ok.connect(self._on_news_loaded)
        self._news_worker.failed.connect(self._on_news_failed)
        self._news_worker.finished.connect(self._on_news_finished)
        self._news_worker.start()

    def _clear_news(self):
        self._news_rows = {}
        while self.news_list_layout.count():
            item = self.news_list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _on_news_loaded(self, items):
        common.remove_shimmers(self.news_list_layout)
        self._news_items = items
        self._render_news()

    def _on_news_failed(self, error):
        common.remove_shimmers(self.news_list_layout)
        self.news_status.setText("Falha ao carregar")
        label = QLabel(f"Não foi possível carregar as notícias.\n{error}")
        label.setObjectName("errorLabel")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.news_list_layout.addWidget(label)

    def _on_news_finished(self):
        self.news_refresh.setEnabled(True)

    def load_tech_news(self):
        if self._tech_worker and self._tech_worker.isRunning():
            return
        self.tech_status.setText("Carregando…")
        self.tech_refresh.setEnabled(False)
        self._clear_tech()
        for _ in range(3):
            sk = common.SkeletonShimmer()
            sk.setObjectName("newsCard")
            sk.setFixedHeight(40)
            self.tech_list_layout.addWidget(sk)
        self._tech_worker = DashTechWorker(self)
        self._tech_worker.finished_ok.connect(self._on_tech_loaded)
        self._tech_worker.failed.connect(self._on_tech_failed)
        self._tech_worker.finished.connect(self._on_tech_finished)
        self._tech_worker.start()

    def _clear_tech(self):
        self._tech_rows = {}
        while self.tech_list_layout.count():
            item = self.tech_list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _on_tech_loaded(self, items):
        common.remove_shimmers(self.tech_list_layout)
        self._tech_items = items
        self._render_tech()

    def _on_tech_failed(self, error):
        common.remove_shimmers(self.tech_list_layout)
        self.tech_status.setText("Falha ao carregar")
        label = QLabel(f"Não foi possível carregar as notícias de tecnologia.\n{error}")
        label.setObjectName("errorLabel")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tech_list_layout.addWidget(label)

    def _on_tech_finished(self):
        self.tech_refresh.setEnabled(True)

    def _render_tech(self):
        state = news._load_state()
        hidden_urls = {entry["url"] for entry in state["hidden"]}
        seen_urls = set(state["seen"])
        self._clear_tech()
        shown = [item for item in self._tech_items if item["url"] not in hidden_urls]
        if not shown:
            label = QLabel("Nenhuma notícia de tecnologia disponível.")
            label.setObjectName("emptyLabel")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tech_list_layout.addWidget(label)
            self.tech_status.setText("")
            return
        for item in shown:
            row = DashNewsRow(item)
            row.clicked.connect(self._open_news)
            row.set_seen(item["url"] in seen_urls)
            self._tech_rows[item["url"]] = row
            self.tech_list_layout.addWidget(row)
        self.tech_status.setText(f"{len(shown)} notícias")

    def _render_news(self):
        state = news._load_state()
        hidden_urls = {entry["url"] for entry in state["hidden"]}
        seen_urls = set(state["seen"])
        self._clear_news()
        shown = [item for item in self._news_items if item["url"] not in hidden_urls]
        if not shown:
            label = QLabel("Nenhuma notícia disponível.")
            label.setObjectName("emptyLabel")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.news_list_layout.addWidget(label)
            self.news_status.setText("")
            return
        for item in shown:
            row = DashNewsRow(item)
            row.clicked.connect(self._open_news)
            row.set_seen(item["url"] in seen_urls)
            self._news_rows[item["url"]] = row
            self.news_list_layout.addWidget(row)
        self.news_status.setText(f"{len(shown)} notícias")

    def _open_news(self, url):
        state = news._load_state()
        if url not in state["seen"]:
            state["seen"] = state["seen"] + [url]
            news._save_state(state)
        row = self._news_rows.get(url) or self._tech_rows.get(url)
        if row is not None:
            row.set_seen(True)
        QDesktopServices.openUrl(QUrl(url))

    def shutdown(self):
        if self._weather_worker and self._weather_worker.isRunning():
            self._weather_worker.requestInterruption()
            if not self._weather_worker.wait(2500):
                self._weather_worker.terminate()
                self._weather_worker.wait()
        if self._news_worker and self._news_worker.isRunning():
            self._news_worker.requestInterruption()
            if not self._news_worker.wait(2500):
                self._news_worker.terminate()
                self._news_worker.wait()
        if self._tech_worker and self._tech_worker.isRunning():
            self._tech_worker.requestInterruption()
            if not self._tech_worker.wait(2500):
                self._tech_worker.terminate()
                self._tech_worker.wait()
