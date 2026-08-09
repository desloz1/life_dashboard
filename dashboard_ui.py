import datetime

import qtawesome as qta
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import common
import reminders as rem
import theme
from weather_ui import WeatherWorker, format_full_date


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

    def _update_clock(self):
        now = datetime.datetime.now()
        self.greeting_label.setText(f"{greeting()} 👋")
        self.date_label.setText(f"{format_full_date(now.date())} · {now:%H:%M:%S}")

    def refresh(self):
        self._update_clock()
        self._refresh_reminders()
        self._refresh_tasks()

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

    def shutdown(self):
        if self._weather_worker and self._weather_worker.isRunning():
            self._weather_worker.requestInterruption()
            if not self._weather_worker.wait(2500):
                self._weather_worker.terminate()
                self._weather_worker.wait()
