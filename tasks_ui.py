import datetime

import qtawesome as qta
from PySide6.QtCore import QDate, QSize, Qt, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

import common
import tasks as tasks_mod
import theme

PRIORITY_NAMES = {"alta": "Alta", "media": "Média", "baixa": "Baixa"}
PRIORITY_LEVELS = {"alta": 0, "media": 1, "baixa": 2, "": 3}


class TaskDialog(QDialog):
    def __init__(self, parent=None, task=None):
        super().__init__(parent)
        self.setWindowTitle("Nova tarefa" if task is None else "Editar tarefa")
        self.setMinimumWidth(420)

        form = QFormLayout(self)
        self.title_edit = QLineEdit()
        form.addRow("Título:", self.title_edit)
        self.desc_edit = QLineEdit()
        form.addRow("Descrição:", self.desc_edit)

        self.priority_combo = QComboBox()
        self.priority_combo.addItem("Sem prioridade", "")
        self.priority_combo.addItem("Alta", "alta")
        self.priority_combo.addItem("Média", "media")
        self.priority_combo.addItem("Baixa", "baixa")
        form.addRow("Prioridade:", self.priority_combo)

        self.category_edit = QLineEdit()
        self.category_edit.setPlaceholderText("ex.: Trabalho, Pessoal, Estudo…")
        form.addRow("Categoria:", self.category_edit)

        self.recurrence_combo = QComboBox()
        for name, key in (("Nenhuma", ""), ("Diária", "diaria"), ("Semanal", "semanal"), ("Mensal", "mensal")):
            self.recurrence_combo.addItem(name, key)
        form.addRow("Recorrência:", self.recurrence_combo)

        self.no_date_check = QCheckBox("Sem data")
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        self.date_edit.setDate(QDate.currentDate())
        form.addRow(self.no_date_check, self.date_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

        self.no_date_check.toggled.connect(self._toggle_date)

        if task is not None:
            self.title_edit.setText(task.title)
            self.desc_edit.setText(task.description)
            idx = self.priority_combo.findData(task.priority)
            self.priority_combo.setCurrentIndex(idx if idx >= 0 else 0)
            self.category_edit.setText(task.category)
            idx = self.recurrence_combo.findData(task.recurrence)
            self.recurrence_combo.setCurrentIndex(idx if idx >= 0 else 0)
            if task.due:
                self.date_edit.setDate(QDate.fromString(task.due, "yyyy-MM-dd"))
            else:
                self.no_date_check.setChecked(True)

    def _toggle_date(self, checked):
        self.date_edit.setEnabled(not checked)

    def _on_accept(self):
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(self, "Tarefa", "Informe um título.")
            return
        self._result = {
            "title": title,
            "description": self.desc_edit.text().strip(),
            "priority": self.priority_combo.currentData(),
            "category": self.category_edit.text().strip(),
            "recurrence": self.recurrence_combo.currentData(),
            "due": "" if self.no_date_check.isChecked() else self.date_edit.date().toString("yyyy-MM-dd"),
        }
        self.accept()

    def result_data(self):
        return getattr(self, "_result", None)


def _due_state(task, today):
    if not task.due:
        return "none", ""
    try:
        due = datetime.date.fromisoformat(task.due)
    except (ValueError, TypeError):
        return "none", task.due
    if due < today:
        return "overdue", "Atrasada"
    if due == today:
        return "today", "Hoje"
    if due == today + datetime.timedelta(days=1):
        return "tomorrow", "Amanhã"
    return "future", due.strftime("%d/%m")


class TaskCard(QFrame):
    toggle_requested = Signal(str)
    edit_requested = Signal(str)
    delete_requested = Signal(str)

    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.task = task
        self.setObjectName("taskCard")
        if task.completed:
            self.setProperty("completed", True)
        state, _ = _due_state(task, datetime.date.today())
        if state == "overdue" and not task.completed:
            self.setProperty("overdue", True)
        self.style().unpolish(self)
        self.style().polish(self)
        common.make_shadow(self, y=3, blur=16)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
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

        meta_parts = []
        if task.priority:
            meta_parts.append(PRIORITY_NAMES.get(task.priority, task.priority))
        if task.category:
            meta_parts.append(task.category)
        if task.recurrence:
            meta_parts.append(tasks_mod.RECURRENCE_NAMES.get(task.recurrence, task.recurrence))
        state, label = _due_state(task, datetime.date.today())
        if state != "none":
            meta_parts.append(label)
        if meta_parts:
            meta = QLabel(" · ".join(meta_parts))
            meta.setObjectName("taskMeta")
            meta.setToolTip(task.description or task.title)
            text_col.addWidget(meta)
        layout.addLayout(text_col, 1)

        actions = QWidget()
        actions.setObjectName("taskActions")
        action_layout = QHBoxLayout(actions)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(2)

        edit_btn = QToolButton()
        edit_btn.setObjectName("cardBtn")
        edit_btn.setIcon(qta.icon("fa5s.pen", color=theme.MUTED))
        edit_btn.setIconSize(QSize(14, 14))
        edit_btn.setFixedSize(24, 24)
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setToolTip("Editar")
        edit_btn.clicked.connect(lambda: self.edit_requested.emit(task.id))

        delete_btn = QToolButton()
        delete_btn.setObjectName("cardBtn")
        delete_btn.setIcon(qta.icon("fa5s.trash-alt", color=theme.DANGER))
        delete_btn.setIconSize(QSize(14, 14))
        delete_btn.setFixedSize(24, 24)
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.setToolTip("Excluir")
        delete_btn.clicked.connect(lambda: self.delete_requested.emit(task.id))

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


class TasksView(QWidget):
    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self._search = ""
        self._status = "all"
        self._priority = "all"
        self._sort = "date"

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = common.make_title("fa5s.tasks", "Tarefas")
        self.status = QLabel("")
        self.status.setObjectName("status")
        self.add_btn = QPushButton(" Nova tarefa")
        self.add_btn.setObjectName("refreshBtn")
        self.add_btn.setIcon(qta.icon("fa5s.plus", color="#ffffff"))
        self.add_btn.setIconSize(QSize(15, 15))
        self.add_btn.clicked.connect(self._add_task)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.status)
        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("newsSearch")
        self.search_edit.setPlaceholderText("Buscar tarefas…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setFixedWidth(220)
        self.search_edit.textChanged.connect(self._on_search)
        header.addWidget(self.search_edit)
        header.addWidget(self.add_btn)
        root.addLayout(header)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setObjectName("taskProgress")
        root.addWidget(self.progress)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)
        self._status_group = QButtonGroup(self)
        self._status_group.setExclusive(True)
        self._status_buttons = {}
        for key, label in (("all", "Todas"), ("pending", "Pendentes"), ("done", "Concluídas")):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setObjectName("filterBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setChecked(key == "all")
            self._status_group.addButton(btn)
            self._status_buttons[key] = btn
            btn.toggled.connect(lambda checked, k=key: self._set_status(k, checked))
            toolbar.addWidget(btn)
        toolbar.addSpacing(8)
        self._priority_group = QButtonGroup(self)
        self._priority_group.setExclusive(True)
        self._priority_buttons = {}
        for key, label in (("all", "Qualquer prioridade"), ("alta", "Alta"), ("media", "Média"), ("baixa", "Baixa")):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setObjectName("filterBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setChecked(key == "all")
            self._priority_group.addButton(btn)
            self._priority_buttons[key] = btn
            btn.toggled.connect(lambda checked, k=key: self._set_priority(k, checked))
            toolbar.addWidget(btn)
        toolbar.addStretch()
        toolbar.addWidget(QLabel("Ordenar por"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItem("Data", "date")
        self.sort_combo.addItem("Prioridade", "priority")
        self.sort_combo.setFixedWidth(150)
        self.sort_combo.currentIndexChanged.connect(self.refresh)
        toolbar.addWidget(self.sort_combo)
        root.addLayout(toolbar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setObjectName("scrollArea")
        self.list_host = QWidget()
        self.list_layout = QVBoxLayout(self.list_host)
        self.list_layout.setContentsMargins(6, 0, 6, 6)
        self.list_layout.setSpacing(10)
        self.list_layout.addStretch()
        self.scroll.setWidget(self.list_host)
        root.addWidget(self.scroll, 1)

        self.refresh()

    def _on_search(self, text):
        self._search = text.strip().lower()
        self.refresh()

    def _set_status(self, key, checked):
        if checked:
            self._status = key
            self.refresh()

    def _set_priority(self, key, checked):
        if checked:
            self._priority = key
            self.refresh()

    def _matches(self, task):
        if self._status == "pending" and task.completed:
            return False
        if self._status == "done" and not task.completed:
            return False
        if self._priority != "all" and task.priority != self._priority:
            return False
        if self._search and self._search not in (task.title + " " + (task.description or "")).lower():
            return False
        return True

    def _sort_key(self, task):
        today = datetime.date.today()
        overdue = 0 if _due_state(task, today)[0] == "overdue" else 1
        completed = 2 if task.completed else 0
        if self._sort == "priority":
            return (completed, PRIORITY_LEVELS.get(task.priority, 3), overdue, task.due or "9999-12-31")
        return (completed, overdue, task.due or "9999-12-31")

    def refresh(self):
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        visible = [t for t in self.manager.tasks if self._matches(t)]
        visible.sort(key=self._sort_key)

        for task in visible:
            card = TaskCard(task)
            card.toggle_requested.connect(self._toggle)
            card.edit_requested.connect(self._edit_task)
            card.delete_requested.connect(self._delete)
            self.list_layout.insertWidget(self.list_layout.count() - 1, card)

        total = len(self.manager.tasks)
        done = sum(1 for t in self.manager.tasks if t.completed)
        self.progress.setValue(int(done * 100 / total) if total else 0)
        self.progress.setFormat(f"{done} de {total} concluídas" if total else "Nenhuma tarefa")
        self.progress.setVisible(total > 0)

        if not total:
            empty = QLabel("Nenhuma tarefa criada ainda.\nClique em \"+ Nova tarefa\" para começar.")
            empty.setObjectName("errorLabel")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.list_layout.insertWidget(0, empty)
            self.status.setText("")
        elif not visible:
            empty = QLabel("Nenhuma tarefa encontrada para os filtros.")
            empty.setObjectName("errorLabel")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.list_layout.insertWidget(0, empty)
            self.status.setText(f"{total} tarefas · filtro")
        else:
            pending = sum(1 for t in visible if not t.completed)
            self.status.setText(
                f"{len(visible)} tarefas" + (f" · {pending} pendente{'s' if pending != 1 else ''}" if pending else "")
            )

    def _add_task(self):
        dialog = TaskDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.result_data()
            self.manager.add(data["title"], data["description"], data["due"],
                             priority=data["priority"], category=data["category"],
                             recurrence=data["recurrence"])
            self.refresh()

    def _edit_task(self, task_id):
        task = next((t for t in self.manager.tasks if t.id == task_id), None)
        if task is None:
            return
        dialog = TaskDialog(self, task=task)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.result_data()
            task.title = data["title"]
            task.description = data["description"]
            task.priority = data["priority"]
            task.category = data["category"]
            task.recurrence = data["recurrence"]
            task.due = data["due"]
            if not task.due or task.due >= datetime.date.today().isoformat():
                task.overdue_notified = ""
            self.manager.update(task)
            self.refresh()

    def _delete(self, task_id):
        task = next((t for t in self.manager.tasks if t.id == task_id), None)
        if task is None:
            return
        answer = QMessageBox.question(
            self,
            "Excluir tarefa",
            f"Excluir \"{task.title}\"?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.manager.remove(task_id)
            self.refresh()

    def _toggle(self, task_id):
        self.manager.toggle(task_id)
        self.refresh()

