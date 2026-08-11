import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

import common
import reminders as rem
import theme

NEWS = "news"
TASK = "task"
REMINDER = "reminder"
NOTE = "note"

SECTIONS = (
    (NEWS, "Notícias"),
    (TASK, "Tarefas"),
    (REMINDER, "Lembretes"),
    (NOTE, "Notas"),
)

KIND_ICON = {
    NEWS: "fa5s.newspaper",
    TASK: "fa5s.tasks",
    REMINDER: "fa5s.bell",
    NOTE: "fa5s.sticky-note",
}


def _kind_color(kind):
    if kind == TASK:
        return theme.WARN
    if kind == REMINDER:
        return theme.OK
    if kind == NOTE:
        return theme.ACCENT_HOVER
    return theme.ACCENT

PRIORITY_NAMES = {"alta": "Alta", "media": "Média", "baixa": "Baixa"}
POOL_NAMES = {"feed": "Feed", "saved": "Salva", "hidden": "Oculto"}


def _snippet(text, limit=90):
    text = (text or "").replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _due_label(task):
    if not task.due:
        return ""
    try:
        due = datetime.date.fromisoformat(task.due)
    except (ValueError, TypeError):
        return ""
    today = datetime.date.today()
    if due < today:
        return "Atrasada"
    if due == today:
        return "Hoje"
    if due == today + datetime.timedelta(days=1):
        return "Amanhã"
    return due.strftime("%d/%m")


def _result(kind, rid, title, snippet, extra, pool=None):
    return {
        "kind": kind,
        "id": rid,
        "title": title,
        "snippet": snippet,
        "extra": extra,
        "pool": pool,
        "icon": KIND_ICON[kind],
        "color": _kind_color(kind),
    }


def collect_results(query, news_pool, tasks, reminders, notes):
    """Agrega resultados de busca sobre notícias, tarefas, lembretes e notas."""
    q = (query or "").strip().lower()
    results = []
    if not q:
        return results

    for url, (pool, item) in news_pool.items():
        haystack = " ".join(
            (item.get("title", ""), item.get("category", ""), item.get("source", ""))
        ).lower()
        if q in haystack:
            results.append(_result(
                NEWS, url, item.get("title", ""), item.get("category", ""),
                item.get("source") or POOL_NAMES.get(pool, pool), pool=pool,
            ))

    for task in tasks.search(q):
        parts = []
        if task.priority:
            parts.append(PRIORITY_NAMES.get(task.priority, task.priority))
        if task.category:
            parts.append(task.category)
        label = _due_label(task)
        if label:
            parts.append(label)
        results.append(_result(
            TASK, task.id, task.title, _snippet(task.description),
            " · ".join(parts) or ("Concluída" if task.completed else "Tarefa"),
        ))

    for reminder in reminders.search(q):
        results.append(_result(
            REMINDER, reminder.id, reminder.title, _snippet(reminder.description),
            rem.describe_schedule(reminder),
        ))

    for note in notes.search(q):
        results.append(_result(
            NOTE, note.id, note.title, _snippet(note.content),
            note.category or ("Fixada" if note.pinned else "Nota"),
        ))

    return results


class SearchResultRow(QFrame):
    activated = Signal(object)
    hovered = Signal(object)

    def __init__(self, result, parent=None):
        super().__init__(parent)
        self.result = result
        self.setObjectName("searchRow")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("selected", False)
        self._repolish()

        metrics = QFontMetrics(QLabel().font())

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(10)

        icon = QLabel()
        icon.setObjectName("searchIcon")
        icon.setFixedWidth(20)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setPixmap(common.icon(result["icon"], result["color"], 15))
        layout.addWidget(icon)

        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        title = QLabel(metrics.elidedText(result["title"], Qt.TextElideMode.ElideRight, 360))
        title.setObjectName("searchTitle")
        title.setToolTip(result["title"])
        text_col.addWidget(title)
        snippet = QLabel(metrics.elidedText(result.get("snippet") or "", Qt.TextElideMode.ElideRight, 420))
        snippet.setObjectName("searchSnippet")
        text_col.addWidget(snippet)
        layout.addLayout(text_col, 1)

        extra = result.get("extra") or ""
        if extra:
            tag = QLabel(metrics.elidedText(extra, Qt.TextElideMode.ElideRight, 170))
            tag.setObjectName("searchTag")
            tag.setToolTip(extra)
            layout.addWidget(tag)

    def _repolish(self):
        self.style().unpolish(self)
        self.style().polish(self)

    def set_selected(self, selected):
        self.setProperty("selected", selected)
        self._repolish()
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.activated.emit(self.result)
        super().mouseReleaseEvent(event)

    def enterEvent(self, event):
        self.hovered.emit(self.result)
        super().enterEvent(event)


class GlobalSearchDialog(QDialog):
    def __init__(self, news_view, tasks, reminders, notes, initial_query="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Busca global")
        self.resize(580, 540)
        self._chosen = None
        self._results = []
        self._row_widgets = []
        self._selected = -1
        self._news_pool = self._build_news_pool(news_view)
        self._tasks = tasks
        self._reminders = reminders
        self._notes = notes

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("newsSearch")
        self.search_edit.setPlaceholderText("Buscar em notícias, notas, tarefas e lembretes…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._on_text)
        root.addWidget(self.search_edit)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setObjectName("scrollArea")
        self.host = QWidget()
        self.list_layout = QVBoxLayout(self.host)
        self.list_layout.setContentsMargins(6, 0, 6, 6)
        self.list_layout.setSpacing(6)
        self.list_layout.addStretch()
        self.scroll.setWidget(self.host)
        root.addWidget(self.scroll, 1)

        self.search_edit.setText(initial_query)

    @staticmethod
    def _build_news_pool(news_view):
        pool = {}
        for item in news_view._items:
            pool[item["url"]] = ("feed", item)
        for item in news_view._state.get("saved", []):
            pool.setdefault(item["url"], ("saved", item))
        for item in news_view._state.get("hidden", []):
            pool.setdefault(item["url"], ("hidden", item))
        return pool

    @property
    def chosen(self):
        return self._chosen

    def _on_text(self, text):
        self._results = collect_results(text, self._news_pool, self._tasks, self._reminders, self._notes)
        self._render()

    def _render(self):
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._row_widgets = []
        self._selected = -1

        if not self._results:
            msg = ("Digite para buscar em notícias, notas, tarefas e lembretes."
                   if not self.search_edit.text() else "Nenhum resultado encontrado.")
            label = QLabel(msg)
            label.setObjectName("searchEmpty")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.list_layout.insertWidget(0, label)
            return

        for kind, title in SECTIONS:
            section = [r for r in self._results if r["kind"] == kind]
            if not section:
                continue
            header = QLabel(f"{title} · {len(section)}")
            header.setObjectName("searchSection")
            self.list_layout.insertWidget(self.list_layout.count() - 1, header)
            for result in section:
                row = SearchResultRow(result)
                row.activated.connect(self._activate)
                row.hovered.connect(self._on_row_hover)
                self.list_layout.insertWidget(self.list_layout.count() - 1, row)
                self._row_widgets.append(row)
        self._select(0)

    def _select(self, index):
        total = len(self._row_widgets)
        if total == 0:
            return
        index = max(0, min(index, total - 1))
        if index == self._selected:
            return
        if 0 <= self._selected < total:
            self._row_widgets[self._selected].set_selected(False)
        self._selected = index
        self._row_widgets[index].set_selected(True)
        self.scroll.ensureWidgetVisible(self._row_widgets[index])

    def _on_row_hover(self, result):
        for index, row in enumerate(self._row_widgets):
            if row.result is result:
                self._select(index)
                return

    def _activate(self, result):
        self._chosen = result
        self.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Up:
            self._select(self._selected - 1)
            event.accept()
        elif event.key() == Qt.Key.Key_Down:
            self._select(self._selected + 1)
            event.accept()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if 0 <= self._selected < len(self._results):
                self._activate(self._results[self._selected])
            event.accept()
        elif event.key() == Qt.Key.Key_Escape:
            self.reject()
            event.accept()
        else:
            super().keyPressEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self.search_edit.setFocus()
        self.search_edit.selectAll()
