import calendar
import datetime

import qtawesome as qta
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

import common
import holidays
import theme
from tasks_ui import PRIORITY_NAMES, TaskDialog

WEEKDAYS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
MONTHS = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


def _date_from_iso(text):
    try:
        return datetime.date.fromisoformat(text)
    except (ValueError, TypeError):
        return None


def _day_label(date):
    today = datetime.date.today()
    if date == today:
        return "Hoje"
    if date == today + datetime.timedelta(days=1):
        return "Amanhã"
    if date < today:
        return f"{WEEKDAYS[date.weekday()]}, {date.day:02d}/{date.month:02d} · atrasado"
    return f"{WEEKDAYS[date.weekday()]}, {date.day:02d}/{date.month:02d}"


class AgendaTaskRow(QFrame):
    toggle_requested = Signal(str)
    edit_requested = Signal(str)

    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.task = task
        self.setObjectName("agendaRow")
        if task.completed:
            self.setProperty("completed", True)
        self.style().unpolish(self)
        self.style().polish(self)
        common.make_shadow(self, y=2, blur=12)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        self.checkbox = QCheckBox()
        self.checkbox.setObjectName("taskCheck")
        self.checkbox.setChecked(task.completed)
        self.checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.checkbox.toggled.connect(lambda checked: self.toggle_requested.emit(task.id))
        layout.addWidget(self.checkbox)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        self.title = QLabel(task.title)
        self.title.setObjectName("taskTitle")
        text_col.addWidget(self.title)
        if task.description:
            desc = QLabel(task.description)
            desc.setObjectName("taskMeta")
            desc.setWordWrap(True)
            text_col.addWidget(desc)

        badges = QHBoxLayout()
        badges.setSpacing(6)
        if task.priority:
            prio = QLabel(PRIORITY_NAMES.get(task.priority, task.priority))
            prio.setObjectName("prioBadge")
            prio.setProperty("level", task.priority)
            prio.style().unpolish(prio)
            prio.style().polish(prio)
            badges.addWidget(prio)
        if task.category:
            cat = QLabel(task.category)
            cat.setObjectName("catBadge")
            badges.addWidget(cat)
        badges.addStretch()
        text_col.addLayout(badges)
        text_col.addStretch()
        layout.addLayout(text_col, 1)

        edit_btn = QPushButton(" Editar")
        edit_btn.setObjectName("secondaryBtn")
        edit_btn.setIcon(qta.icon("fa5s.pen", color=theme.TEXT))
        edit_btn.setIconSize(QSize(13, 13))
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.clicked.connect(lambda: self.edit_requested.emit(task.id))
        layout.addWidget(edit_btn)

        self._apply_completed_style()

    def _apply_completed_style(self):
        font = QFont(self.title.font())
        font.setStrikeOut(self.task.completed)
        self.title.setFont(font)


class AgendaHolidayRow(QFrame):
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.setObjectName("holidayRow")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        icon = QLabel()
        icon.setObjectName("holidayIcon")
        icon.setPixmap(qta.icon("fa5s.star", color=theme.WARN).pixmap(18, 18))
        layout.addWidget(icon)

        badge = QLabel("Feriado")
        badge.setObjectName("holidayBadge")
        layout.addWidget(badge)

        title = QLabel(name)
        title.setObjectName("holidayName")
        layout.addWidget(title, 1)


class AgendaView(QWidget):
    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self._search = ""
        self._mode = "grouped"
        self._month_cursor = datetime.date.today().replace(day=1)
        self._selected_date = datetime.date.today()
        self._week_start = _monday_of(datetime.date.today())

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        header = QHBoxLayout()
        header.addWidget(common.make_title("fa5s.calendar-alt", "Agenda"))
        header.addStretch()
        self.status = QLabel("")
        self.status.setObjectName("status")
        header.addWidget(self.status)
        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("newsSearch")
        self.search_edit.setPlaceholderText("Buscar na agenda…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setFixedWidth(200)
        self.search_edit.textChanged.connect(self._on_search)
        header.addWidget(self.search_edit)

        self._mode_group = QButtonGroup(self)
        self._mode_group.setExclusive(True)
        self._mode_buttons = {}
        for key, label in (("grouped", "Por dia"), ("month", "Mês"), ("week", "Semana")):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setObjectName("filterBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setChecked(key == self._mode)
            self._mode_group.addButton(btn)
            self._mode_buttons[key] = btn
            btn.toggled.connect(lambda checked, k=key: self._set_mode(k, checked))
            header.addWidget(btn)
        self.refresh_btn = QPushButton(" Atualizar")
        self.refresh_btn.setObjectName("refreshBtn")
        self.refresh_btn.setIcon(qta.icon("fa5s.sync-alt", color="#ffffff"))
        self.refresh_btn.clicked.connect(self.refresh)
        header.addWidget(self.refresh_btn)
        root.addLayout(header)

        self.stack = QStackedWidget()
        self.grouped_page = self._build_grouped_page()
        self.month_page = self._build_month_page()
        self.week_page = self._build_week_page()
        self.stack.addWidget(self.grouped_page)
        self.stack.addWidget(self.month_page)
        self.stack.addWidget(self.week_page)
        root.addWidget(self.stack, 1)

        self._show_mode()
        self.refresh()

    # ---------- pages ----------

    def _build_grouped_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        self.grouped_scroll = QScrollArea()
        self.grouped_scroll.setWidgetResizable(True)
        self.grouped_scroll.setObjectName("scrollArea")
        self.grouped_host = QWidget()
        self.grouped_layout = QVBoxLayout(self.grouped_host)
        self.grouped_layout.setContentsMargins(6, 0, 6, 6)
        self.grouped_layout.setSpacing(8)
        self.grouped_layout.addStretch()
        self.grouped_scroll.setWidget(self.grouped_host)
        layout.addWidget(self.grouped_scroll)
        return page

    def _build_month_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        nav = QHBoxLayout()
        self.month_prev = QPushButton("◀")
        self.month_prev.setObjectName("navBtn")
        self.month_prev.setFixedWidth(36)
        self.month_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self.month_prev.clicked.connect(lambda: self._shift_month(-1))
        self.month_next = QPushButton("▶")
        self.month_next.setObjectName("navBtn")
        self.month_next.setFixedWidth(36)
        self.month_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.month_next.clicked.connect(lambda: self._shift_month(1))
        self.month_label = QLabel("")
        self.month_label.setObjectName("calTitle")
        nav.addWidget(self.month_prev)
        nav.addWidget(self.month_label)
        nav.addStretch()
        nav.addWidget(self.month_next)
        layout.addLayout(nav)

        self.month_grid = QGridLayout()
        self.month_grid.setSpacing(6)
        layout.addLayout(self.month_grid)

        self.month_day_header = QLabel("")
        self.month_day_header.setObjectName("dayHeader")
        layout.addWidget(self.month_day_header)

        self.month_list = QScrollArea()
        self.month_list.setWidgetResizable(True)
        self.month_list.setObjectName("scrollArea")
        self.month_host = QWidget()
        self.month_layout = QVBoxLayout(self.month_host)
        self.month_layout.setContentsMargins(6, 0, 6, 6)
        self.month_layout.setSpacing(8)
        self.month_layout.addStretch()
        self.month_list.setWidget(self.month_host)
        layout.addWidget(self.month_list, 1)
        return page

    def _build_week_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        nav = QHBoxLayout()
        self.week_prev = QPushButton("◀")
        self.week_prev.setObjectName("navBtn")
        self.week_prev.setFixedWidth(36)
        self.week_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self.week_prev.clicked.connect(lambda: self._shift_week(-7))
        self.week_next = QPushButton("▶")
        self.week_next.setObjectName("navBtn")
        self.week_next.setFixedWidth(36)
        self.week_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.week_next.clicked.connect(lambda: self._shift_week(7))
        self.week_label = QLabel("")
        self.week_label.setObjectName("calTitle")
        nav.addWidget(self.week_prev)
        nav.addWidget(self.week_label)
        nav.addStretch()
        nav.addWidget(self.week_next)
        layout.addLayout(nav)

        self.week_scroll = QScrollArea()
        self.week_scroll.setWidgetResizable(True)
        self.week_scroll.setObjectName("scrollArea")
        self.week_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.week_host = QWidget()
        self.week_row = QHBoxLayout(self.week_host)
        self.week_row.setContentsMargins(6, 0, 6, 6)
        self.week_row.setSpacing(10)
        self.week_scroll.setWidget(self.week_host)
        layout.addWidget(self.week_scroll)
        return page

    # ---------- state ----------

    def _on_search(self, text):
        self._search = text.strip().lower()
        self.refresh()

    def _set_mode(self, key, checked):
        if checked:
            self._mode = key
            self._show_mode()
            self.refresh()

    def _show_mode(self):
        self.stack.setCurrentIndex({"grouped": 0, "month": 1, "week": 2}[self._mode])

    def _shift_month(self, delta):
        year = self._month_cursor.year
        month = self._month_cursor.month + delta
        if month < 1:
            month, year = 12, year - 1
        elif month > 12:
            month, year = 1, year + 1
        self._month_cursor = datetime.date(year, month, 1)
        self.refresh()

    def _shift_week(self, delta):
        self._week_start = self._week_start + datetime.timedelta(days=delta)
        self.refresh()

    # ---------- data ----------

    def _tasks_for(self, date):
        return [t for t in self.manager.tasks if _date_from_iso(t.due) == date and self._matches(t)]

    def _matches(self, task):
        if not self._search:
            return True
        return self._search in (task.title + " " + (task.description or "")).lower()

    def _clear_layout(self, layout):
        while layout.count() > 1:
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _add_row(self, layout, task):
        row = AgendaTaskRow(task)
        row.toggle_requested.connect(self._toggle_task)
        row.edit_requested.connect(self._edit_task)
        layout.insertWidget(layout.count() - 1, row)

    def _add_header(self, layout, text):
        label = QLabel(text)
        label.setObjectName("dayHeader")
        layout.insertWidget(layout.count() - 1, label)

    def _add_holidays(self, layout, date):
        for name in holidays.holidays_for(date):
            layout.insertWidget(layout.count() - 1, AgendaHolidayRow(name))

    # ---------- rendering ----------

    def refresh(self):
        if self._mode == "grouped":
            self._render_grouped()
        elif self._mode == "month":
            self._render_month()
        else:
            self._render_week()
        total = len([t for t in self.manager.tasks if t.due])
        self.status.setText(f"{total} compromissos agendados")

    def _render_grouped(self):
        self._clear_layout(self.grouped_layout)
        today = datetime.date.today()

        def due_date(task):
            return _date_from_iso(task.due)

        dated = [t for t in self.manager.tasks if due_date(t) and self._matches(t)]
        by_day = {}
        for task in dated:
            by_day.setdefault(due_date(task), []).append(task)

        for date in sorted(by_day):
            tasks = by_day[date]
            tasks.sort(key=lambda t: (PRIORITY_NAMES.get(t.priority, ""), t.title))
            self._add_header(self.grouped_layout, _day_label(date))
            self._add_holidays(self.grouped_layout, date)
            for task in tasks:
                self._add_row(self.grouped_layout, task)

        if not by_day:
            empty = QLabel("Nenhum compromisso agendado.")
            empty.setObjectName("errorLabel")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grouped_layout.insertWidget(0, empty)

    def _render_month(self):
        while self.month_grid.count():
            item = self.month_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        year, month = self._month_cursor.year, self._month_cursor.month
        self.month_label.setText(f"{MONTHS[month - 1].capitalize()} {year}")
        today = datetime.date.today()
        first_weekday = self._month_cursor.weekday()
        days_in_month = calendar.monthrange(year, month)[1]

        for col, name in enumerate(WEEKDAYS):
            header = QLabel(name)
            header.setObjectName("dayHeader")
            header.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.month_grid.addWidget(header, 0, col)

        first_cell_date = self._month_cursor - datetime.timedelta(days=first_weekday)
        for cell in range(42):
            date = first_cell_date + datetime.timedelta(days=cell)
            btn = QPushButton()
            btn.setObjectName("calCell")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if date.month != month:
                btn.setProperty("empty", True)
                btn.setEnabled(False)
            else:
                tasks = self._tasks_for(date)
                suffix = "  •" * min(len(tasks), 3)
                if holidays.holidays_for(date):
                    suffix += "  ★"
                    btn.setProperty("holiday", True)
                btn.setText(f"{date.day}{suffix}")
                if date == today:
                    btn.setProperty("today", True)
                if date == self._selected_date:
                    btn.setProperty("selected", True)
                    btn.setChecked(True)
                btn.setCheckable(True)
                btn.clicked.connect(lambda checked=False, d=date: self._select_day(d))
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            self.month_grid.addWidget(btn, 1 + cell // 7, cell % 7)

        self.month_day_header.setText(_day_label(self._selected_date))
        self._clear_layout(self.month_layout)
        self._add_holidays(self.month_layout, self._selected_date)
        selected_tasks = self._tasks_for(self._selected_date)
        for task in sorted(selected_tasks, key=lambda t: (t.completed, PRIORITY_NAMES.get(t.priority, ""), t.title)):
            self._add_row(self.month_layout, task)
        if not selected_tasks:
            empty = QLabel("Nenhum compromisso neste dia.")
            empty.setObjectName("errorLabel")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.month_layout.insertWidget(0, empty)

    def _select_day(self, date):
        self._selected_date = date
        self.refresh()

    def _render_week(self):
        while self.week_row.count():
            item = self.week_row.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        today = datetime.date.today()
        self.week_label.setText(
            f"{self._week_start.day:02d}/{self._week_start.month:02d} a "
            f"{(self._week_start + datetime.timedelta(days=6)).day:02d}/{(self._week_start + datetime.timedelta(days=6)).month:02d}"
        )

        for offset in range(7):
            date = self._week_start + datetime.timedelta(days=offset)
            col = QFrame()
            col.setObjectName("weekCol")
            col.setFixedWidth(190)
            col_layout = QVBoxLayout(col)
            col_layout.setContentsMargins(10, 10, 10, 10)
            col_layout.setSpacing(6)

            head = QLabel(f"{WEEKDAYS[offset]}, {date.day:02d}/{date.month:02d}")
            head.setObjectName("weekColHead")
            if date == today:
                head.setProperty("today", True)
                head.style().unpolish(head)
                head.style().polish(head)
            head.setAlignment(Qt.AlignmentFlag.AlignCenter)
            col_layout.addWidget(head)

            self._add_holidays(col_layout, date)

            tasks = self._tasks_for(date)
            if not tasks:
                none = QLabel("—")
                none.setObjectName("taskMeta")
                none.setAlignment(Qt.AlignmentFlag.AlignCenter)
                none.setStyleSheet(f"color: {theme.MUTED}; padding: 6px;")
                col_layout.addWidget(none)
            for task in sorted(tasks, key=lambda t: (t.completed, PRIORITY_NAMES.get(t.priority, ""), t.title)):
                row = AgendaTaskRow(task)
                row.toggle_requested.connect(self._toggle_task)
                row.edit_requested.connect(self._edit_task)
                col_layout.addWidget(row)
            col_layout.addStretch()
            self.week_row.addWidget(col)

        self.week_row.addStretch()

    # ---------- actions ----------

    def _toggle_task(self, task_id):
        self.manager.toggle(task_id)
        self.refresh()

    def _edit_task(self, task_id):
        task = next((t for t in self.manager.tasks if t.id == task_id), None)
        if task is None:
            return
        from PySide6.QtWidgets import QDialog
        dialog = TaskDialog(self, task=task)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.result_data()
            task.title = data["title"]
            task.description = data["description"]
            task.priority = data["priority"]
            task.category = data["category"]
            task.due = data["due"]
            self.manager.update(task)
            self.refresh()


def _monday_of(date):
    return date - datetime.timedelta(days=date.weekday())
