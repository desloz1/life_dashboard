import datetime

import qtawesome as qta
from PySide6.QtCore import QDate, QSize, Qt, QTime, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QTimeEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

import common
import reminders as rem
import theme

TYPE_STYLE = {
    "one_time": ("fa5s.bell", "#5b8cff"),
    "daily": ("fa5s.redo", "#34c38f"),
    "weekly": ("fa5s.calendar-week", "#f0a04b"),
    "monthly": ("fa5s.calendar-check", "#b07bf0"),
}


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

        when_date = self.date_edit.date().toString("yyyy-MM-dd")
        when_time = self.time_edit.time().toString("HH:mm")
        if trigger_type == "one_time":
            hour, minute = (int(x) for x in when_time.split(":"))
            try:
                when = datetime.datetime.strptime(when_date, "%Y-%m-%d").replace(hour=hour, minute=minute)
            except ValueError:
                QMessageBox.warning(self, "Lembrete", "Data inválida.")
                return
            if when <= datetime.datetime.now():
                QMessageBox.warning(
                    self,
                    "Lembrete",
                    "O horário informado já passou. Escolha uma data/hora futura.",
                )
                return

        self._result = {
            "title": title,
            "description": self.desc_edit.text().strip(),
            "trigger_type": trigger_type,
            "time": when_time,
            "date": when_date if trigger_type == "one_time" else "",
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
    snooze_requested = Signal(str, int)

    def __init__(self, reminder, parent=None):
        super().__init__(parent)
        self.setObjectName("reminderCard")
        if not reminder.enabled:
            self.setProperty("paused", True)
        if rem.is_overdue(reminder):
            self.setProperty("overdue", True)
        self.style().unpolish(self)
        self.style().polish(self)
        common.make_shadow(self, y=3, blur=16)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        icon_name, icon_color = TYPE_STYLE.get(reminder.trigger_type, TYPE_STYLE["one_time"])
        icon_label = QLabel()
        icon_label.setObjectName("reminderIcon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if not reminder.enabled:
            icon_label.setPixmap(common.icon("fa5s.bell-slash", theme.MUTED, 18))
        elif rem.is_snoozed(reminder):
            icon_label.setPixmap(common.icon("fa5s.moon", theme.MUTED, 18))
        else:
            icon_label.setPixmap(common.icon(icon_name, icon_color, 18))
        layout.addWidget(icon_label)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        self.title = QLabel(reminder.title)
        self.title.setObjectName("reminderTitle")
        text_col.addWidget(self.title)
        meta_parts = [rem.describe_schedule(reminder)]
        if rem.is_snoozed(reminder):
            meta_parts.append(rem.format_next(reminder.snooze_until))
        else:
            next_text = rem.format_next(reminder.next_trigger)
            if next_text:
                meta_parts.append(next_text)
        meta = QLabel(" · ".join(meta_parts))
        meta.setObjectName("reminderMeta")
        meta.setToolTip(reminder.description or reminder.title)
        text_col.addWidget(meta)
        layout.addLayout(text_col, 1)

        actions = QWidget()
        actions.setObjectName("reminderActions")
        action_layout = QHBoxLayout(actions)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(2)

        snooze_menu = QMenu(self)
        for minutes in (5, 15, 30):
            action = snooze_menu.addAction(f"Adiar {minutes} min")
            action.triggered.connect(
                lambda checked=False, m=minutes: self.snooze_requested.emit(reminder.id, m)
            )
        self.snooze_btn = QToolButton()
        self.snooze_btn.setObjectName("cardBtn")
        self.snooze_btn.setIcon(qta.icon("fa5s.moon", color=theme.MUTED))
        self.snooze_btn.setIconSize(QSize(14, 14))
        self.snooze_btn.setFixedSize(24, 24)
        self.snooze_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.snooze_btn.setToolTip("Adiar")
        self.snooze_btn.setMenu(snooze_menu)
        self.snooze_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        self.toggle_btn = QToolButton()
        self.toggle_btn.setObjectName("cardBtn")
        self.toggle_btn.setIcon(qta.icon("fa5s.pause" if reminder.enabled else "fa5s.play", color=theme.ACCENT))
        self.toggle_btn.setIconSize(QSize(14, 14))
        self.toggle_btn.setFixedSize(24, 24)
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.setToolTip("Pausar" if reminder.enabled else "Ativar")
        self.toggle_btn.clicked.connect(lambda: self.toggle_requested.emit(reminder.id))

        edit_btn = QToolButton()
        edit_btn.setObjectName("cardBtn")
        edit_btn.setIcon(qta.icon("fa5s.pen", color=theme.MUTED))
        edit_btn.setIconSize(QSize(14, 14))
        edit_btn.setFixedSize(24, 24)
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setToolTip("Editar")
        edit_btn.clicked.connect(lambda: self.edit_requested.emit(reminder.id))

        delete_btn = QToolButton()
        delete_btn.setObjectName("cardBtn")
        delete_btn.setIcon(qta.icon("fa5s.trash-alt", color=theme.DANGER))
        delete_btn.setIconSize(QSize(14, 14))
        delete_btn.setFixedSize(24, 24)
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.setToolTip("Excluir")
        delete_btn.clicked.connect(lambda: self.delete_requested.emit(reminder.id))

        action_layout.addWidget(self.snooze_btn)
        action_layout.addWidget(self.toggle_btn)
        action_layout.addWidget(edit_btn)
        action_layout.addWidget(delete_btn)
        self.actions_widget = actions
        actions.setVisible(False)
        layout.addWidget(actions)

    def enterEvent(self, event):
        self.actions_widget.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.rect().contains(self.mapFromGlobal(QCursor.pos())):
            self.actions_widget.setVisible(False)
        super().leaveEvent(event)


class RemindersView(QWidget):
    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self._search = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        title = common.make_title("fa5s.bell", "Lembretes")
        self.status = QLabel("")
        self.status.setObjectName("status")
        self.add_btn = QPushButton(" Novo lembrete")
        self.add_btn.setObjectName("refreshBtn")
        self.add_btn.setIcon(qta.icon("fa5s.plus", color="#ffffff"))
        self.add_btn.setIconSize(QSize(15, 15))
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self._add_reminder)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.status)
        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("newsSearch")
        self.search_edit.setPlaceholderText("Buscar lembretes…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setFixedWidth(220)
        self.search_edit.textChanged.connect(self._on_search)
        header.addWidget(self.search_edit)
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

    def _on_search(self, text):
        self._search = text.strip().lower()
        self.refresh()

    def refresh(self):
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        now = datetime.datetime.now()
        visible = [
            r for r in self.manager.reminders
            if not self._search or self._search in (r.title + " " + r.description).lower()
        ]

        def sort_key(reminder):
            overdue = rem.is_overdue(reminder, now)
            return (
                0 if overdue else (1 if reminder.enabled else 2),
                reminder.next_trigger or "9999-12-31T23:59",
            )

        ordered = sorted(visible, key=sort_key)
        overdue_count = sum(1 for r in visible if rem.is_overdue(r, now))
        for reminder in ordered:
            card = ReminderCard(reminder)
            card.edit_requested.connect(self._edit_reminder)
            card.delete_requested.connect(self._delete_reminder)
            card.toggle_requested.connect(self._toggle_reminder)
            card.snooze_requested.connect(self._snooze_reminder)
            self.list_layout.insertWidget(self.list_layout.count() - 1, card)

        if not self.manager.reminders:
            empty = QLabel("Nenhum lembrete criado ainda.\nClique em \"+ Novo lembrete\" para começar.")
            empty.setObjectName("errorLabel")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.list_layout.insertWidget(0, empty)
            self.status.setText("")
        elif not ordered:
            empty = QLabel("Nenhum lembrete encontrado para a busca.")
            empty.setObjectName("errorLabel")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.list_layout.insertWidget(0, empty)
            self.status.setText(f"{len(visible)} lembretes · busca")
        else:
            self.status.setText(
                f"{len(visible)} lembretes" + (f" · {overdue_count} atrasado{'s' if overdue_count != 1 else ''}" if overdue_count else "")
            )

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

    def _snooze_reminder(self, reminder_id, minutes):
        self.manager.snooze(reminder_id, minutes)
        self.refresh()
