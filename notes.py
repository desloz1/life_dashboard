import html as _html
import json
import os
import re
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime

import log

logger = log.get_logger("life_dashboard.notes")

_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PATH = os.path.join(_DIR, "notas.json")
DEFAULT_ATTACH_DIR = os.path.join(_DIR, "anexos")

PRIORITY_NAMES = {"alta": "Alta", "media": "Média", "baixa": "Baixa"}
PRIORITY_LEVELS = {"alta": 0, "media": 1, "baixa": 2, "": 3}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".ico"}


@dataclass
class Note:
    id: str
    title: str
    content: str = ""
    pinned: bool = False
    priority: str = ""  # "", "alta", "media", "baixa"
    category: str = ""
    created: str = ""  # ISO datetime
    updated: str = ""  # ISO datetime
    attachments: list = field(default_factory=list)  # [{"id", "name", "path"}]


class NoteManager:
    def __init__(self, path=DEFAULT_PATH):
        self.path = path
        self.notes = []
        self.load()

    def load(self):
        self.notes = []
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            for item in data or []:
                if not isinstance(item, dict) or not item.get("id"):
                    continue
                attachments = item.get("attachments") or []
                if not isinstance(attachments, list):
                    attachments = []
                self.notes.append(Note(
                    id=item["id"],
                    title=item.get("title", "Sem título"),
                    content=item.get("content", ""),
                    pinned=bool(item.get("pinned", False)),
                    priority=item.get("priority", ""),
                    category=item.get("category", ""),
                    created=item.get("created", ""),
                    updated=item.get("updated", ""),
                    attachments=[a for a in attachments if isinstance(a, dict) and a.get("id") and a.get("path")],
                ))
        except (OSError, ValueError) as exc:
            logger.error("Falha ao carregar notas de %s: %s", self.path, exc)
            return

    def save(self):
        data = []
        for n in self.notes:
            data.append({
                "id": n.id,
                "title": n.title,
                "content": n.content,
                "pinned": n.pinned,
                "priority": n.priority,
                "category": n.category,
                "created": n.created,
                "updated": n.updated,
                "attachments": n.attachments,
            })
        try:
            with open(self.path, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(data, ensure_ascii=False, indent=2))
        except OSError as exc:
            logger.error("Falha ao salvar notas em %s: %s", self.path, exc)

    def add(self, title, content="", priority="", category=""):
        now = datetime.now().isoformat(timespec="seconds")
        note = Note(id=uuid.uuid4().hex, title=title or "Sem título", content=content,
                    created=now, updated=now, priority=priority, category=category)
        self.notes.append(note)
        self.save()
        return note

    def update(self, note):
        note.updated = datetime.now().isoformat(timespec="seconds")
        self.save()

    def remove(self, note_id):
        note = self.get(note_id)
        if note is not None:
            for att in note.attachments:
                self._delete_copy(att)
        self.notes = [n for n in self.notes if n.id != note_id]
        self.save()

    def toggle_pin(self, note_id):
        for n in self.notes:
            if n.id == note_id:
                n.pinned = not n.pinned
                self.save()
                return n
        return None

    def get(self, note_id):
        return next((n for n in self.notes if n.id == note_id), None)

    def _delete_copy(self, att):
        path = self.attachment_path(att)
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError as exc:
                logger.error("Falha ao remover anexo %s: %s", path, exc)

    def attachment_path(self, att):
        """Caminho absoluto do anexo (aceita caminho relativo ou absoluto)."""
        rel = att.get("path", "")
        if not rel:
            return None
        if os.path.isabs(rel):
            return rel
        return os.path.join(_DIR, rel)

    def attach(self, note_id, source_path):
        """Copia o arquivo para a pasta local e registra na nota."""
        note = self.get(note_id)
        if note is None or not source_path or not os.path.exists(source_path):
            return None
        ext = os.path.splitext(source_path)[1].lower()
        aid = uuid.uuid4().hex
        try:
            os.makedirs(DEFAULT_ATTACH_DIR, exist_ok=True)
            dest = os.path.join(DEFAULT_ATTACH_DIR, f"{aid}{ext}")
            shutil.copy2(source_path, dest)
        except OSError as exc:
            logger.error("Falha ao anexar arquivo %s: %s", source_path, exc)
            return None
        att = {
            "id": aid,
            "name": os.path.basename(source_path),
            "path": os.path.relpath(dest, _DIR),
        }
        note.attachments.append(att)
        note.updated = datetime.now().isoformat(timespec="seconds")
        self.save()
        return att

    def detach(self, note_id, attachment_id):
        note = self.get(note_id)
        if note is None:
            return False
        for att in note.attachments:
            if att.get("id") == attachment_id:
                self._delete_copy(att)
                note.attachments.remove(att)
                note.updated = datetime.now().isoformat(timespec="seconds")
                self.save()
                return True
        return False

    def _sort_key(self, note):
        updated = note.updated or ""
        return (
            0 if note.pinned else 1,
            PRIORITY_LEVELS.get(note.priority, 3),
            updated if updated else "0000-01-01T00:00:00",
            note.title.lower(),
        )

    def sorted_notes(self):
        return sorted(self.notes, key=self._sort_key)

    def search(self, query):
        q = (query or "").strip().lower()
        if not q:
            return self.sorted_notes()
        result = [n for n in self.notes if q in f"{n.title} {n.content} {n.category}".lower()]
        result.sort(key=self._sort_key)
        return result


def _inline(md):
    md = _html.escape(md, quote=False)
    md = re.sub(r"`([^`]+)`", r"<code>\1</code>", md)
    md = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', md)
    md = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", md)
    md = re.sub(r"__([^_]+)__", r"<b>\1</b>", md)
    md = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", md)
    md = re.sub(r"_([^_]+)_", r"<i>\1</i>", md)
    md = re.sub(r"~([^~]+)~", r"<s>\1</s>", md)
    return md


def markdown_to_html(text):
    """Converte um subconjunto de Markdown em HTML. Sem dependências externas."""
    lines = (text or "").splitlines()
    out = []
    stack = []  # tipos de lista abertos: 'ul' | 'ol'
    i = 0

    def close_lists():
        while stack:
            out.append(f"</{stack.pop()}>")

    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()

        if not stripped:
            close_lists()
            i += 1
            continue

        if stripped.startswith("```"):
            close_lists()
            code = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1  # pula o fechamento
            block = _html.escape("\n".join(code))
            out.append(f"<pre>{block}</pre>")
            continue

        heading = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading:
            close_lists()
            level = len(heading.group(1))
            out.append(f"<h{level}>{_inline(heading.group(2))}</h{level}>")
            i += 1
            continue

        if re.match(r"^\s*-{3,}\s*$", line):
            close_lists()
            out.append("<hr>")
            i += 1
            continue

        if stripped.startswith(">"):
            close_lists()
            out.append(f"<blockquote>{_inline(stripped[1:].strip())}</blockquote>")
            i += 1
            continue

        um = re.match(r"^\s*[-*]\s+(.*)$", line)
        om = re.match(r"^\s*\d+\.\s+(.*)$", line)
        if um or om:
            target = "ol" if om else "ul"
            if not stack or stack[-1] != target:
                if stack:
                    out.append(f"</{stack.pop()}>")
                out.append(f"<{target}>")
                stack.append(target)
            content = um.group(1) if um else om.group(1)
            task = re.match(r"^\[([ xX])\]\s+(.*)$", content)
            if task:
                glyph = "&#9745;" if task.group(1).lower() == "x" else "&#9744;"
                content = f'<span class="task">{glyph}</span> {_inline(task.group(2))}'
            out.append(f"<li>{content}</li>")
            i += 1
            continue

        close_lists()
        para = [_inline(stripped)]
        i += 1
        while i < len(lines):
            nxt = lines[i].rstrip()
            if not nxt.strip():
                break
            if (re.match(r"^(#{1,6})\s+", nxt) or re.match(r"^\s*-{3,}\s*$", nxt)
                    or re.match(r"^\s*[-*]\s+", nxt) or re.match(r"^\s*\d+\.\s+", nxt)
                    or nxt.strip().startswith(">") or nxt.strip().startswith("```")):
                break
            para.append(_inline(nxt.strip()))
            i += 1
        out.append(f"<p>{'<br>'.join(para)}</p>")

    close_lists()
    return "\n".join(out)


def preview_html(content):
    """HTML completo para o preview legível, com cores do tema."""
    import theme
    def color(name, default):
        return getattr(theme, name, None) or default
    c_text = color("TEXT", "#1f2937")
    c_accent = color("ACCENT", "#3b82f6")
    c_btn = color("BTN", "#f3f4f6")
    c_border = color("BORDER", "#e5e7eb")
    c_muted = color("MUTED", "#6b7280")
    style = f"""
        body {{ color: {c_text}; font-family: 'Segoe UI'; font-size: 14px; line-height: 1.55; }}
        h1, h2, h3, h4 {{ color: {c_text}; margin: 14px 0 6px; }}
        h1 {{ font-size: 22px; }} h2 {{ font-size: 19px; }} h3 {{ font-size: 16px; }}
        p {{ margin: 8px 0; }}
        a {{ color: {c_accent}; }}
        code {{ background: {c_btn}; border: 1px solid {c_border}; border-radius: 4px; padding: 1px 5px; font-family: 'Consolas'; }}
        pre {{ background: {c_btn}; border: 1px solid {c_border}; border-radius: 8px; padding: 10px; overflow-x: auto; }}
        pre code {{ background: transparent; border: none; padding: 0; }}
        blockquote {{ border-left: 3px solid {c_accent}; margin: 8px 0; padding: 4px 12px; color: {c_muted}; }}
        hr {{ border: none; border-top: 1px solid {c_border}; margin: 12px 0; }}
        ul, ol {{ margin: 6px 0 6px 4px; padding-left: 22px; }}
        li {{ margin: 3px 0; }}
        .task {{ color: {c_accent}; }}
    """
    return f'<html><head><style>{style}</style></head><body>{markdown_to_html(content)}</body></html>'
