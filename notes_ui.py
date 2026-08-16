import datetime
import os

import qtawesome as qta
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTextBrowser,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

import common
import notes as notes_mod
import theme

PRIORITY_NAMES = notes_mod.PRIORITY_NAMES


def _format_dt(iso):
    if not iso:
        return ""
    try:
        dt = datetime.datetime.fromisoformat(iso)
    except (ValueError, TypeError):
        return ""
    return dt.strftime("%d/%m/%Y %H:%M")


class AttachmentStrip(QWidget):
    open_requested = Signal(dict)
    remove_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(64)
        self._row = QHBoxLayout(self)
        self._row.setContentsMargins(0, 0, 0, 0)
        self._row.setSpacing(8)
        self._row.addStretch()
        self._attachments = []
        self.setVisible(False)

    def set_attachments(self, attachments):
        while self._row.count() > 1:
            item = self._row.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._attachments = list(attachments or [])
        for att in self._attachments:
            self._row.insertWidget(self._row.count() - 1, self._chip(att))
        self.setVisible(bool(self._attachments))

    def _chip(self, att):
        chip = QFrame()
        chip.setObjectName("attachChip")
        layout = QHBoxLayout(chip)
        layout.setContentsMargins(6, 4, 4, 4)
        layout.setSpacing(6)

        thumb = QLabel()
        thumb.setObjectName("attachThumb")
        thumb.setFixedSize(44, 36)
        thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        path = self._path(att)
        is_image = os.path.splitext(att.get("name", ""))[1].lower() in notes_mod.IMAGE_EXTENSIONS
        if is_image and path and os.path.exists(path):
            pix = QPixmap(path)
            if not pix.isNull():
                thumb.setPixmap(pix.scaled(44, 36, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                           Qt.TransformationMode.SmoothTransformation))
        else:
            thumb.setPixmap(qta.icon("fa5s.paperclip", color=theme.MUTED).pixmap(18, 18))

        name = QLabel(att.get("name", ""))
        name.setObjectName("attachName")
        name.setToolTip(att.get("name", ""))

        open_btn = QToolButton()
        open_btn.setObjectName("cardBtn")
        open_btn.setIcon(qta.icon("fa5s.external-link-alt", color=theme.ACCENT))
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.setToolTip("Abrir arquivo")
        open_btn.clicked.connect(lambda checked=False, a=att: self.open_requested.emit(a))

        remove_btn = QToolButton()
        remove_btn.setObjectName("cardBtn")
        remove_btn.setIcon(qta.icon("fa5s.times", color=theme.DANGER))
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.setToolTip("Remover anexo")
        remove_btn.clicked.connect(lambda checked=False, a=att: self.remove_requested.emit(a.get("id", "")))

        layout.addWidget(thumb)
        layout.addWidget(name)
        layout.addWidget(open_btn)
        layout.addWidget(remove_btn)
        return chip

    @staticmethod
    def _path(att):
        rel = att.get("path", "")
        if not rel:
            return None
        if os.path.isabs(rel):
            return rel
        return os.path.join(os.path.dirname(os.path.abspath(notes_mod.__file__)), rel)


class NoteCard(QFrame):
    clicked = Signal(str)

    def __init__(self, note, active=False, parent=None):
        super().__init__(parent)
        self.note = note
        self.setObjectName("noteCard")
        self.setProperty("active", active)
        self.style().unpolish(self)
        self.style().polish(self)
        common.make_shadow(self, y=2, blur=14)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        text_col = QVBoxLayout()
        text_col.setSpacing(3)
        top = QHBoxLayout()
        top.setSpacing(6)
        title = QLabel(note.title or "Sem título")
        title.setObjectName("noteTitle")
        title.setWordWrap(True)
        top.addWidget(title, 1)
        if note.attachments:
            clip = QLabel()
            clip.setPixmap(qta.icon("fa5s.paperclip", color=theme.MUTED).pixmap(13, 13))
            clip.setToolTip(f"{len(note.attachments)} anexo{'s' if len(note.attachments) != 1 else ''}")
            top.addWidget(clip)
        if note.pinned:
            pin = QLabel()
            pin.setPixmap(qta.icon("fa5s.thumbtack", color=theme.ACCENT).pixmap(13, 13))
            pin.setToolTip("Fixada")
            top.addWidget(pin)
        if note.priority:
            prio = QLabel(PRIORITY_NAMES.get(note.priority, note.priority))
            prio.setObjectName("prioBadge")
            prio.setProperty("level", note.priority)
            prio.style().unpolish(prio)
            prio.style().polish(prio)
            top.addWidget(prio)
        text_col.addLayout(top)

        snippet_text = (note.content or "").replace("\n", " ").strip()
        if not snippet_text:
            snippet_text = "Nota vazia"
        snippet = QLabel(snippet_text)
        snippet.setObjectName("noteSnippet")
        snippet.setWordWrap(True)
        text_col.addWidget(snippet)
        text_col.addStretch()
        layout.addLayout(text_col, 1)

        self.setMinimumHeight(68)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.note.id)
        super().mouseReleaseEvent(event)


class NotesView(QWidget):
    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self._search = ""
        self._current_id = None
        self._editing = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = common.make_title("fa5s.sticky-note", "Notas")
        self.status = QLabel("")
        self.status.setObjectName("status")
        self.add_btn = QPushButton(" Nova nota")
        self.add_btn.setObjectName("refreshBtn")
        self.add_btn.setIcon(qta.icon("fa5s.plus", color="#ffffff"))
        self.add_btn.setIconSize(QSize(15, 15))
        self.add_btn.clicked.connect(self._new_note)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.status)
        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("newsSearch")
        self.search_edit.setPlaceholderText("Buscar notas…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setFixedWidth(220)
        self.search_edit.textChanged.connect(self._on_search)
        header.addWidget(self.search_edit)
        header.addWidget(self.add_btn)
        root.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(12)

        self.list_scroll = QScrollArea()
        self.list_scroll.setWidgetResizable(True)
        self.list_scroll.setObjectName("scrollArea")
        self.list_scroll.setFixedWidth(260)
        self.list_host = QWidget()
        self.list_layout = QVBoxLayout(self.list_host)
        self.list_layout.setContentsMargins(6, 0, 6, 6)
        self.list_layout.setSpacing(8)
        self.list_layout.addStretch()
        self.list_scroll.setWidget(self.list_host)
        body.addWidget(self.list_scroll)

        self.detail = QStackedWidget()
        self.detail.setObjectName("scrollArea")
        body.addWidget(self.detail, 1)
        root.addLayout(body, 1)

        self._build_placeholder()
        self._build_preview_page()
        self._build_edit_page()

        self.refresh()

    # ---------- páginas do painel direito ----------

    def _build_placeholder(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addStretch()
        label = QLabel("Selecione ou crie uma nota")
        label.setObjectName("emptyLabel")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        layout.addStretch()
        self.detail.addWidget(page)

    def _build_preview_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(8)
        self.preview_title = QLabel("")
        self.preview_title.setObjectName("noteTitleEdit")
        self.preview_title.setWordWrap(True)
        top.addWidget(self.preview_title, 1)

        badges = QHBoxLayout()
        badges.setSpacing(6)
        self.preview_prio = QLabel("")
        self.preview_prio.setObjectName("prioBadge")
        self.preview_prio.hide()
        badges.addWidget(self.preview_prio)
        self.preview_cat = QLabel("")
        self.preview_cat.setObjectName("catBadge")
        self.preview_cat.hide()
        badges.addWidget(self.preview_cat)
        top.addLayout(badges)
        layout.addLayout(top)

        meta_row = QHBoxLayout()
        self.preview_updated = QLabel("")
        self.preview_updated.setObjectName("noteMeta")
        meta_row.addWidget(self.preview_updated)
        meta_row.addStretch()
        self.pin_btn = QPushButton("")
        self.pin_btn.setObjectName("secondaryBtn")
        self.pin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pin_btn.clicked.connect(self._toggle_pin)
        meta_row.addWidget(self.pin_btn)
        edit_btn = QPushButton(" Editar")
        edit_btn.setObjectName("secondaryBtn")
        edit_btn.setIcon(qta.icon("fa5s.pen", color=theme.TEXT))
        edit_btn.setIconSize(QSize(13, 13))
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.clicked.connect(self._start_edit)
        meta_row.addWidget(edit_btn)
        export_btn = QPushButton(" Exportar")
        export_btn.setObjectName("secondaryBtn")
        export_btn.setIcon(qta.icon("fa5s.file-export", color=theme.TEXT))
        export_btn.setIconSize(QSize(13, 13))
        export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_btn.clicked.connect(self._export_note)
        meta_row.addWidget(export_btn)
        attach_btn = QPushButton(" Anexar")
        attach_btn.setObjectName("secondaryBtn")
        attach_btn.setIcon(qta.icon("fa5s.paperclip", color=theme.TEXT))
        attach_btn.setIconSize(QSize(13, 13))
        attach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        attach_btn.clicked.connect(self._attach_files)
        meta_row.addWidget(attach_btn)
        delete_btn = QPushButton(" Excluir")
        delete_btn.setObjectName("dangerBtn")
        delete_btn.setIcon(qta.icon("fa5s.trash-alt", color=theme.DANGER))
        delete_btn.setIconSize(QSize(13, 13))
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.clicked.connect(self._delete_note)
        meta_row.addWidget(delete_btn)
        layout.addLayout(meta_row)

        self.preview_strip = AttachmentStrip()
        self.preview_strip.open_requested.connect(self._open_attachment)
        self.preview_strip.remove_requested.connect(self._remove_attachment)
        layout.addWidget(self.preview_strip)

        self.preview = QTextBrowser()
        self.preview.setObjectName("notePreview")
        self.preview.setOpenExternalLinks(True)
        layout.addWidget(self.preview, 1)

        self.detail.addWidget(page)

    def _build_edit_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.title_edit = QLineEdit()
        self.title_edit.setObjectName("noteTitleEdit")
        self.title_edit.setPlaceholderText("Título da nota")
        layout.addWidget(self.title_edit)

        fields = QHBoxLayout()
        fields.setSpacing(8)
        self.priority_combo = QComboBox()
        self.priority_combo.addItem("Sem prioridade", "")
        self.priority_combo.addItem("Alta", "alta")
        self.priority_combo.addItem("Média", "media")
        self.priority_combo.addItem("Baixa", "baixa")
        fields.addWidget(self.priority_combo)
        self.category_edit = QLineEdit()
        self.category_edit.setPlaceholderText("Categoria")
        self.category_edit.setFixedWidth(200)
        fields.addWidget(self.category_edit)
        hint = QLabel("Formatação: # título, **negrito**, *itálico*, - item, - [x] tarefa")
        hint.setObjectName("noteMeta")
        fields.addWidget(hint)
        fields.addStretch()
        layout.addLayout(fields)

        self.edit_strip = AttachmentStrip()
        self.edit_strip.open_requested.connect(self._open_attachment)
        self.edit_strip.remove_requested.connect(self._remove_attachment)
        layout.addWidget(self.edit_strip)

        fmt = QHBoxLayout()
        fmt.setSpacing(4)
        for icon, tip, action in (
            ("fa5s.bold", "Negrito (**)**", lambda: self._wrap_selection("**", "**")),
            ("fa5s.italic", "Itálico (*)", lambda: self._wrap_selection("*", "*")),
            ("fa5s.strikethrough", "Riscado (~~)", lambda: self._wrap_selection("~~", "~~")),
            ("fa5s.code", "Código (`)", lambda: self._wrap_selection("`", "`")),
            ("fa5s.link", "Link ([texto](url))", lambda: self._wrap_link()),
            ("fa5s.heading", "Título (#)", lambda: self._line_prefix("# ")),
            ("fa5s.list-ul", "Lista (- )", lambda: self._line_prefix("- ")),
            ("fa5s.check-square", "Tarefa (- [ ])", lambda: self._line_prefix("- [ ] ")),
            ("fa5s.quote-left", "Citação (>)", lambda: self._line_prefix("> ")),
        ):
            btn = QToolButton()
            btn.setObjectName("cardBtn")
            btn.setIcon(qta.icon(icon, color=theme.TEXT))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(tip)
            btn.clicked.connect(action)
            fmt.addWidget(btn)
        fmt.addStretch()
        layout.addLayout(fmt)

        self.editor = QTextEdit()
        self.editor.setObjectName("noteEditor")
        self.editor.setAcceptRichText(False)
        self.editor.setPlaceholderText("Escreva sua nota…")
        layout.addWidget(self.editor, 1)

        actions = QHBoxLayout()
        attach_btn = QPushButton(" Anexar")
        attach_btn.setObjectName("secondaryBtn")
        attach_btn.setIcon(qta.icon("fa5s.paperclip", color=theme.TEXT))
        attach_btn.setIconSize(QSize(13, 13))
        attach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        attach_btn.clicked.connect(self._attach_files)
        actions.addWidget(attach_btn)
        actions.addStretch()
        save_btn = QPushButton(" Salvar")
        save_btn.setObjectName("refreshBtn")
        save_btn.setIcon(qta.icon("fa5s.check", color="#ffffff"))
        save_btn.setIconSize(QSize(13, 13))
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._save_note)
        actions.addWidget(save_btn)
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self._cancel_edit)
        actions.addWidget(cancel_btn)
        layout.addLayout(actions)

        self.detail.addWidget(page)

    # ---------- estado ----------

    def _current_note(self):
        if self._current_id is None:
            return None
        return self.manager.get(self._current_id)

    def _on_search(self, text):
        self._search = text.strip().lower()
        self._update_list()

    def _update_list(self):
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        visible = self.manager.search(self._search)
        for note in visible:
            card = NoteCard(note, active=(note.id == self._current_id))
            card.clicked.connect(self._select_note)
            self.list_layout.insertWidget(self.list_layout.count() - 1, card)

        total = len(self.manager.notes)
        pinned = sum(1 for n in self.manager.notes if n.pinned)
        self.status.setText(f"{len(visible)} de {total} notas" + (f" · {pinned} fixada{'s' if pinned != 1 else ''}" if pinned else ""))

    def _update_right(self):
        note = self._current_note()
        if note is None:
            self.detail.setCurrentWidget(self.detail.widget(0))
            return
        if self._editing:
            self.detail.setCurrentWidget(self.detail.widget(2))
            return
        self.detail.setCurrentWidget(self.detail.widget(1))
        self._fill_preview(note)

    def refresh(self):
        self._update_list()
        self._update_right()

    # ---------- preview ----------

    def _fill_preview(self, note):
        self.preview_title.setText(note.title or "Sem título")
        if note.priority:
            self.preview_prio.setText(PRIORITY_NAMES.get(note.priority, note.priority))
            self.preview_prio.setProperty("level", note.priority)
            self.preview_prio.style().unpolish(self.preview_prio)
            self.preview_prio.style().polish(self.preview_prio)
            self.preview_prio.show()
        else:
            self.preview_prio.hide()
        if note.category:
            self.preview_cat.setText(note.category)
            self.preview_cat.show()
        else:
            self.preview_cat.hide()
        self.preview_updated.setText(f"Editada em {_format_dt(note.updated)}" if note.updated else "")
        self.pin_btn.setText(" Desafixar" if note.pinned else " Fixar")
        self.pin_btn.setIcon(qta.icon("fa5s.thumbtack", color=theme.ACCENT if note.pinned else theme.MUTED))
        self.preview_strip.set_attachments(note.attachments)
        self.preview.setHtml(notes_mod.preview_html(note.content))

    # ---------- edição ----------

    def _start_edit(self):
        note = self._current_note()
        if note is None:
            return
        self._editing = True
        self.title_edit.setText(note.title)
        self.editor.setPlainText(note.content)
        self.category_edit.setText(note.category)
        idx = self.priority_combo.findData(note.priority)
        self.priority_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.edit_strip.set_attachments(note.attachments)
        self._update_right()
        self.title_edit.setFocus()

    def _collect_editor(self):
        note = self._current_note()
        if note is None:
            return None
        note.title = self.title_edit.text().strip() or "Sem título"
        note.content = self.editor.toPlainText()
        note.category = self.category_edit.text().strip()
        note.priority = self.priority_combo.currentData()
        self.manager.update(note)
        return note

    def _save_note(self):
        if self._editing:
            self._collect_editor()
        self._editing = False
        self.refresh()

    def _cancel_edit(self):
        self._editing = False
        self._update_right()

    def _wrap_selection(self, before, after):
        cur = self.editor.textCursor()
        text = cur.selectedText()
        if text:
            cur.insertText(f"{before}{text}{after}")
        else:
            cur.insertText(f"{before}{after}")
            cur.setPosition(cur.position() - len(after))
        self.editor.setTextCursor(cur)
        self.editor.setFocus()

    def _wrap_link(self):
        cur = self.editor.textCursor()
        text = cur.selectedText() or "texto"
        cur.insertText(f"[{text}](url)")
        self.editor.setTextCursor(cur)
        self.editor.setFocus()

    def _line_prefix(self, prefix):
        cur = self.editor.textCursor()
        cur.beginEditBlock()
        sel_start = cur.selectionStart()
        sel_end = cur.selectionEnd()
        cur.setPosition(sel_start)
        block_start = cur.block().position()
        pos = block_start
        while pos <= sel_end:
            cur.setPosition(pos)
            cur.insertText(prefix)
            block = cur.block().next()
            if not block.isValid():
                break
            pos = block.position()
        cur.endEditBlock()
        self.editor.setFocus()

    def _save_current_edits(self):
        if self._editing and self._current_note() is not None:
            self._collect_editor()
            self._editing = False

    # ---------- ações ----------

    def _select_note(self, note_id):
        if note_id == self._current_id:
            return
        self._save_current_edits()
        self._current_id = note_id
        self.refresh()

    def _new_note(self):
        self._save_current_edits()
        note = self.manager.add("Nova nota", "")
        self._current_id = note.id
        self.refresh()
        self._start_edit()
        self.title_edit.selectAll()

    def _toggle_pin(self):
        note = self._current_note()
        if note is None:
            return
        self.manager.toggle_pin(note.id)
        self.refresh()

    def _attach_files(self):
        note = self._current_note()
        if note is None:
            return
        files, _ = QFileDialog.getOpenFileNames(self, "Anexar arquivos", "", "Todos os arquivos (*.*)")
        if not files:
            return
        added = 0
        for f in files:
            if self.manager.attach(note.id, f):
                added += 1
        if added:
            self.refresh()
            self.status.setText(f"{added} anexo{'s' if added != 1 else ''} adicionado{'s' if added != 1 else ''}")

    def _open_attachment(self, att):
        path = self.manager.attachment_path(att)
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "Anexo", "Arquivo não encontrado.")
            return
        try:
            os.startfile(path)
        except OSError as exc:
            QMessageBox.warning(self, "Anexo", f"Não foi possível abrir o arquivo:\n{exc}")

    def _remove_attachment(self, attachment_id):
        note = self._current_note()
        if note is None or not attachment_id:
            return
        answer = QMessageBox.question(
            self,
            "Remover anexo",
            "Remover este anexo da nota? O arquivo copiado será excluído.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.manager.detach(note.id, attachment_id)
        self.refresh()

    def _delete_note(self):
        note = self._current_note()
        if note is None:
            return
        answer = QMessageBox.question(
            self,
            "Excluir nota",
            f"Excluir \"{note.title}\"?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.manager.remove(note.id)
        self._current_id = None
        self._editing = False
        self.refresh()

    def _export_note(self):
        note = self._current_note()
        if note is None:
            return
        base = (note.title or "nota").replace("/", "-").replace("\\", "-")
        path, selected = QFileDialog.getSaveFileName(
            self,
            "Exportar nota",
            base + ".md",
            "Markdown (*.md);;Texto (*.txt)",
        )
        if not path:
            return
        content = f"# {note.title or ''}\n\n{note.content}\n"
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
        except OSError as exc:
            QMessageBox.warning(self, "Exportar nota", f"Falha ao salvar o arquivo:\n{exc}")
            return
        self.status.setText(f"Nota exportada para {path}")
