import concurrent.futures
import datetime
import json
import re
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

import qtawesome as qta

import common
import log
import scraper
import theme

logger = log.get_logger("life_dashboard.news")

STATE_FILE = Path(__file__).resolve().parent / "estado_noticias.json"


def _load_state():
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return {
            "saved": data.get("saved", [])[:100],
            "hidden": data.get("hidden", []),
            "seen": list(dict.fromkeys(data.get("seen", [])))[-200:],
        }
    except Exception as exc:
        logger.warning("Falha ao ler %s: %s", STATE_FILE, exc)
        return {"saved": [], "hidden": [], "seen": []}


def _save_state(state):
    try:
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.error("Falha ao salvar %s: %s", STATE_FILE, exc)


def _as_snapshot(item):
    return {
        "title": item.get("title", ""),
        "url": item.get("url", ""),
        "image": item.get("image", ""),
        "category": item.get("category", ""),
        "date": item.get("date", ""),
        "source": item.get("source", ""),
    }


def _relative_time(text):
    value = (text or "").strip()
    if not value:
        return ""
    low = value.lower()
    if low in ("agora", "hoje", "ontem", "anteontem") or low.startswith("há"):
        return value
    match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})(?:\s+(\d{1,2}):(\d{2}))?", value)
    if not match:
        return ""
    day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
    try:
        if match.group(4):
            then = datetime.datetime(year, month, day, int(match.group(4)), int(match.group(5)))
            seconds = (datetime.datetime.now() - then).total_seconds()
        else:
            then = datetime.date(year, month, day)
            seconds = (datetime.date.today() - then).days * 86400
    except ValueError:
        return ""
    if seconds < 0:
        return ""
    if seconds < 3600:
        return "agora"
    hours = int(seconds // 3600)
    if hours < 24:
        return f"há {hours} h"
    days = int(seconds // 86400)
    if days == 1:
        return "ontem"
    if days < 7:
        return f"há {days} dias"
    return value


MONTHS_PT = {
    "janeiro": 1,
    "fevereiro": 2,
    "março": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}


def parse_news_datetime(text, now=None):
    """Converte a data textual de uma notícia em datetime (ou None)."""
    value = (text or "").strip()
    if not value:
        return None
    now = now or datetime.datetime.now()
    low = value.lower()

    if low in ("agora", "hoje"):
        return now
    if low == "ontem":
        return now - datetime.timedelta(days=1)
    if low == "anteontem":
        return now - datetime.timedelta(days=2)

    match = re.fullmatch(r"há\s+(\d+)\s+(minuto|hora|dia)s?", low)
    if match:
        count = int(match.group(1))
        unit = match.group(2)
        if unit.startswith("minuto"):
            return now - datetime.timedelta(minutes=count)
        if unit.startswith("hora"):
            return now - datetime.timedelta(hours=count)
        return now - datetime.timedelta(days=count)

    match = re.fullmatch(
        r"(\d{1,2})/(\d{1,2})/(\d{4})(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?",
        value,
    )
    if match:
        day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        try:
            if match.group(4):
                return datetime.datetime(year, month, day, int(match.group(4)), int(match.group(5)))
            return datetime.datetime(year, month, day)
        except ValueError:
            return None

    match = re.fullmatch(
        r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})(?:\s+(?:às|as|a)\s+(\d{1,2}):(\d{2}))?",
        low,
    )
    if match:
        month = MONTHS_PT.get(match.group(2))
        if month is None:
            return None
        try:
            day = int(match.group(1))
            year = int(match.group(3))
            if match.group(4):
                return datetime.datetime(year, month, day, int(match.group(4)), int(match.group(5)))
            return datetime.datetime(year, month, day)
        except ValueError:
            return None

    return None


def sort_by_date(items, limit=None):
    """Ordena notícias da mais recente para a mais antiga; sem data, por último."""
    dated = []
    undated = []
    for item in items:
        when = parse_news_datetime(item.get("date"))
        if when is not None:
            dated.append((when, item))
        else:
            undated.append(item)
    dated.sort(key=lambda pair: pair[0], reverse=True)
    ordered = [item for _, item in dated] + undated
    if limit is not None:
        return ordered[:limit]
    return ordered


class NewsWorker(QThread):
    finished_ok = Signal(list)
    failed = Signal(str)

    def __init__(self, show_thumbnails, parent=None):
        super().__init__(parent)
        self._show_thumbnails = show_thumbnails

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

        groups = {}
        for item in raw:
            groups.setdefault(item["source"], []).append(item)
        items = []
        for offset in range(max(len(group) for group in groups.values())):
            for source_items in groups.values():
                if offset < len(source_items):
                    items.append(source_items[offset])

        for item in items:
            item["show_thumb"] = self._show_thumbnails
            if not self._show_thumbnails:
                item["image_bytes"] = None

        if self._show_thumbnails and not self.isInterruptionRequested():
            urls = [item["image"] for item in items]
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                for item, data in zip(items, executor.map(common.download_image_bytes, urls)):
                    if self.isInterruptionRequested():
                        return
                    item["image_bytes"] = data

        if not self.isInterruptionRequested():
            self.finished_ok.emit(items)


class NewsCard(QFrame):
    clicked = Signal(str)
    save_requested = Signal(str)
    hide_requested = Signal(str)
    restore_requested = Signal(str)
    hovered = Signal(str)

    def __init__(self, item, restore_mode=False, parent=None):
        super().__init__(parent)
        self._url = item["url"]
        self.setObjectName("newsCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        common.make_shadow(self, y=2, blur=14)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        if item.get("show_thumb", True):
            self.thumb = QLabel()
            self.thumb.setFixedSize(100, 60)
            self.thumb.setObjectName("newsThumb")
            self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pixmap = item.get("pixmap")
            if pixmap is not None:
                self.thumb.setPixmap(common.rounded_pixmap(common.cover_pixmap(pixmap, 100, 74), 10))
            else:
                self.thumb.setPixmap(common.icon("fa5s.newspaper", "#6b7684", 32))
            layout.addWidget(self.thumb)

        text_col = QVBoxLayout()
        text_col.setSpacing(4)

        meta = QHBoxLayout()
        meta.setSpacing(8)
        self.kicker = QLabel(item["category"])
        self.kicker.setObjectName("newsCategory")
        meta.addWidget(self.kicker)
        self.source_badge = QLabel(item.get("source") or "")
        self.source_badge.setObjectName("newsSource")
        meta.addWidget(self.source_badge)
        rel = _relative_time(item.get("date"))
        if rel:
            self.time = QLabel(rel)
            self.time.setObjectName("newsTime")
            meta.addWidget(self.time)
        self.saved_badge = QLabel()
        self.saved_badge.setObjectName("savedBadge")
        self.saved_badge.setToolTip("Salva")
        self.saved_badge.setVisible(False)
        meta.addWidget(self.saved_badge)
        meta.addStretch()

        if restore_mode:
            self.restore_btn = self._icon_btn("fa5s.undo", "Restaurar")
            self.restore_btn.clicked.connect(lambda: self.restore_requested.emit(self._url))
            meta.addWidget(self.restore_btn)
        else:
            self.save_btn = self._icon_btn("fa5s.bookmark", "Salvar para depois")
            self.save_btn.clicked.connect(lambda: self.save_requested.emit(self._url))
            meta.addWidget(self.save_btn)
            self.hide_btn = self._icon_btn("fa5s.eye-slash", "Ocultar")
            self.hide_btn.clicked.connect(lambda: self.hide_requested.emit(self._url))
            meta.addWidget(self.hide_btn)
            self._set_saved(item.get("saved", False))

        text_col.addLayout(meta)

        self.title = QLabel(item["title"])
        self.title.setObjectName("newsTitle")
        self.title.setWordWrap(True)
        self.title.setMaximumHeight(34)
        text_col.addWidget(self.title)
        text_col.addStretch()

        layout.addLayout(text_col, 1)
        self.setMinimumHeight(80)
        self._update_actions_visibility()

    def _icon_btn(self, name, tooltip):
        btn = QPushButton()
        btn.setObjectName("cardBtn")
        btn.setIcon(qta.icon(name, color=theme.MUTED))
        btn.setIconSize(QSize(15, 15))
        btn.setFixedSize(26, 26)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip(tooltip)
        return btn

    def _set_saved(self, saved):
        self.save_btn.setIcon(qta.icon("fa5s.bookmark", color=theme.ACCENT if saved else theme.MUTED))
        if saved:
            self.saved_badge.setPixmap(qta.icon("fa5s.bookmark", color=theme.ACCENT).pixmap(14, 14))
        else:
            self.saved_badge.clear()
        self.saved_badge.setVisible(saved)

    def set_seen(self, seen):
        self.setProperty("seen", "true" if seen else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def _update_actions_visibility(self):
        visible = self.underMouse()
        if hasattr(self, "save_btn"):
            self.save_btn.setVisible(visible)
            self.hide_btn.setVisible(visible)
        if hasattr(self, "restore_btn"):
            self.restore_btn.setVisible(visible)

    def enterEvent(self, event):
        self.hovered.emit(self._url)
        self._update_actions_visibility()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hovered.emit("")
        self._update_actions_visibility()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._url)
        super().mouseReleaseEvent(event)


class FeaturedCard(QFrame):
    clicked = Signal(str)
    save_requested = Signal(str)
    hide_requested = Signal(str)
    hovered = Signal(str)

    def __init__(self, item, parent=None):
        super().__init__(parent)
        self._url = item["url"]
        self.setObjectName("featuredCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        common.make_shadow(self, y=4, blur=22)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        self._source_pixmap = None
        if item.get("show_thumb", True):
            self.thumb = QLabel()
            self.thumb.setObjectName("featuredThumb")
            self.thumb.setFixedHeight(180)
            self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pixmap = item.get("pixmap")
            if pixmap is not None:
                self._source_pixmap = pixmap
                self._refresh_thumb()
            else:
                self.thumb.setStyleSheet(f"background: {theme.THUMB_BG};")
                self.thumb.setPixmap(common.icon("fa5s.newspaper", "#6b7684", 48))
            layout.addWidget(self.thumb)

        self.title = QLabel(item["title"])
        self.title.setObjectName("featuredTitle")
        self.title.setWordWrap(True)
        layout.addWidget(self.title)

        meta = QHBoxLayout()
        meta.setSpacing(8)
        self.kicker = QLabel(item["category"])
        self.kicker.setObjectName("newsCategory")
        meta.addWidget(self.kicker)
        self.source_badge = QLabel(item.get("source") or "")
        self.source_badge.setObjectName("newsSource")
        meta.addWidget(self.source_badge)
        rel = _relative_time(item.get("date"))
        if rel:
            self.time = QLabel(rel)
            self.time.setObjectName("newsTime")
            meta.addWidget(self.time)
        self.saved_badge = QLabel()
        self.saved_badge.setObjectName("savedBadge")
        self.saved_badge.setToolTip("Salva")
        self.saved_badge.setVisible(False)
        meta.addWidget(self.saved_badge)
        meta.addStretch()
        self.save_btn = self._icon_btn("fa5s.bookmark", "Salvar para depois")
        self.save_btn.clicked.connect(lambda: self.save_requested.emit(self._url))
        meta.addWidget(self.save_btn)
        self.hide_btn = self._icon_btn("fa5s.eye-slash", "Ocultar")
        self.hide_btn.clicked.connect(lambda: self.hide_requested.emit(self._url))
        meta.addWidget(self.hide_btn)
        self._set_saved(item.get("saved", False))
        layout.addLayout(meta)
        self._update_actions_visibility()

    def _icon_btn(self, name, tooltip):
        btn = QPushButton()
        btn.setObjectName("cardBtn")
        btn.setIcon(qta.icon(name, color=theme.MUTED))
        btn.setIconSize(QSize(15, 15))
        btn.setFixedSize(26, 26)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip(tooltip)
        return btn

    def _set_saved(self, saved):
        self.save_btn.setIcon(qta.icon("fa5s.bookmark", color=theme.ACCENT if saved else theme.MUTED))
        if saved:
            self.saved_badge.setPixmap(qta.icon("fa5s.bookmark", color=theme.ACCENT).pixmap(14, 14))
        else:
            self.saved_badge.clear()
        self.saved_badge.setVisible(saved)

    def _refresh_thumb(self):
        width = max(self.thumb.width(), 1)
        height = max(self.thumb.height(), 1)
        cover = common.cover_pixmap(self._source_pixmap, width, height)
        self.thumb.setPixmap(common.rounded_pixmap(cover, 12))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._source_pixmap is not None:
            self._refresh_thumb()

    def set_seen(self, seen):
        self.setProperty("seen", "true" if seen else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def _update_actions_visibility(self):
        visible = self.underMouse()
        self.save_btn.setVisible(visible)
        self.hide_btn.setVisible(visible)

    def enterEvent(self, event):
        self.hovered.emit(self._url)
        self._update_actions_visibility()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hovered.emit("")
        self._update_actions_visibility()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._url)
        super().mouseReleaseEvent(event)


class NewsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._items = []
        self._state = _load_state()
        self._tab = "feed"
        self._source_filter = "all"
        self._search = ""
        self._cards = {}
        self._undo_bar = None
        self._undo_timer = None
        self._hovered_url = None
        self._cleared = False
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._setup_shortcuts()

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        header = QHBoxLayout()
        header.addWidget(common.make_title("fa5s.newspaper", "Notícias de Blumenau"))
        header.addStretch()
        self.status = QLabel("")
        self.status.setObjectName("status")
        header.addWidget(self.status)
        self.thumb_check = QCheckBox("Imagens")
        self.thumb_check.setCursor(Qt.CursorShape.PointingHandCursor)
        self.thumb_check.toggled.connect(self.load_news)
        header.addWidget(self.thumb_check)
        self.refresh_btn = QPushButton(" Atualizar")
        self.refresh_btn.setIcon(qta.icon("fa5s.sync-alt", color="#ffffff"))
        self.refresh_btn.setIconSize(QSize(15, 15))
        self.refresh_btn.setObjectName("refreshBtn")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.load_news)
        header.addWidget(self.refresh_btn)
        self.clear_btn = QPushButton(" Limpar")
        self.clear_btn.setIcon(qta.icon("fa5s.trash-alt", color=theme.MUTED))
        self.clear_btn.setIconSize(QSize(15, 15))
        self.clear_btn.setObjectName("secondaryBtn")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.setToolTip("Limpar a lista de notícias carregadas")
        self.clear_btn.clicked.connect(self._clear_feed)
        header.addWidget(self.clear_btn)
        root.addLayout(header)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)
        self._tab_group = QButtonGroup(self)
        self._tab_group.setExclusive(True)
        self._tab_buttons = {}
        for key, label in (("feed", "Feed"), ("saved", "Salvos"), ("hidden", "Ocultos")):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setObjectName("tabBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setChecked(key == "feed")
            self._tab_group.addButton(btn)
            self._tab_buttons[key] = btn
            btn.toggled.connect(lambda checked, k=key: self._set_tab(k, checked))
            toolbar.addWidget(btn)
        toolbar.addStretch()
        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("newsSearch")
        self.search_edit.setPlaceholderText("Buscar notícias…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setFixedWidth(240)
        self.search_edit.textChanged.connect(self._on_search)
        toolbar.addWidget(self.search_edit)
        root.addLayout(toolbar)

        source_row = QHBoxLayout()
        source_row.setSpacing(6)
        self._source_group = QButtonGroup(self)
        self._source_group.setExclusive(True)
        self._source_buttons = {}
        all_btn = QPushButton("Todas")
        all_btn.setCheckable(True)
        all_btn.setChecked(True)
        all_btn.setObjectName("sourceBtn")
        all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._source_group.addButton(all_btn)
        self._source_buttons["all"] = all_btn
        all_btn.toggled.connect(lambda checked: self._set_source("all", checked))
        source_row.addWidget(all_btn)
        for src in scraper.SOURCES:
            btn = QPushButton(src)
            btn.setCheckable(True)
            btn.setObjectName("sourceBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._source_group.addButton(btn)
            self._source_buttons[src] = btn
            btn.toggled.connect(lambda checked, s=src: self._set_source(s, checked))
            source_row.addWidget(btn)
        source_row.addStretch()
        root.addLayout(source_row)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setObjectName("scrollArea")
        self.list_host = QWidget()
        self.list_layout = QVBoxLayout(self.list_host)
        self.list_layout.setContentsMargins(6, 0, 6, 6)
        self.list_layout.setSpacing(4)
        self.list_layout.addStretch()
        self.scroll.setWidget(self.list_host)
        root.addWidget(self.scroll, 1)

        self.load_news()

    def _setup_shortcuts(self):
        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)
        save_shortcut.activated.connect(self._shortcut_save)
        hide_shortcut = QShortcut(QKeySequence("Ctrl+H"), self)
        hide_shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)
        hide_shortcut.activated.connect(self._shortcut_hide)

    def _shortcut_save(self):
        if self._hovered_url:
            self._toggle_save(self._hovered_url)

    def _shortcut_hide(self):
        if self._hovered_url:
            self._hide_item(self._hovered_url)

    def _on_hover(self, url):
        self._hovered_url = url or None

    def clear_hover(self):
        self._hovered_url = None

    def load_news(self):
        if self._worker and self._worker.isRunning():
            return
        self._cleared = False
        self.status.setText("Carregando…")
        self.refresh_btn.setEnabled(False)
        self._clear_cards()
        for _ in range(5):
            sk = common.SkeletonShimmer()
            sk.setObjectName("newsCard")
            sk.setFixedHeight(110)
            layout = QHBoxLayout(sk)
            thumb = QLabel()
            thumb.setFixedSize(theme.THUMB_WIDTH, theme.THUMB_HEIGHT)
            thumb.setStyleSheet(f"background: {theme.THUMB_BG}; border-radius:10px;")
            layout.addWidget(thumb)
            tcol = QVBoxLayout()
            t1 = QLabel("Carregando...")
            t1.setObjectName("newsTitle")
            tcol.addWidget(t1)
            tcol.addStretch()
            layout.addLayout(tcol)
            self.list_layout.insertWidget(self.list_layout.count() - 1, sk)

        self._worker = NewsWorker(self.thumb_check.isChecked(), self)
        self._worker.finished_ok.connect(self._on_loaded)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _clear_feed(self):
        self._cleared = True
        if self._worker and self._worker.isRunning():
            self._worker.requestInterruption()
        self._items = []
        self._render()
        self.status.setText("Lista limpa — Atualizar para recarregar")

    def _clear_undo(self):
        if self._undo_timer is not None:
            self._undo_timer.stop()
            self._undo_timer = None

    def _clear_cards(self):
        self._clear_undo()
        self._cards = {}
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _on_loaded(self, items):
        common.remove_shimmers(self.list_layout)
        if self._cleared:
            return
        self._items = []
        for item in items:
            item["pixmap"] = common.pixmap_from_bytes(item.pop("image_bytes", None))
            self._items.append(item)
        self._render()

    def _on_failed(self, error):
        common.remove_shimmers(self.list_layout)
        self.status.setText("Falha ao carregar notícias")
        label = QLabel(f"Não foi possível carregar as notícias.\n{error}")
        label.setObjectName("errorLabel")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.list_layout.insertWidget(0, label)

    def _on_finished(self):
        self.refresh_btn.setEnabled(True)

    def _set_tab(self, key, checked):
        if not checked:
            return
        self._tab = key
        self._render()

    def _set_source(self, source, checked):
        if not checked:
            return
        self._source_filter = source
        self._render()

    def _on_search(self, text):
        self._search = text.strip().lower()
        self._render()

    def _visible_items(self):
        if self._tab == "feed":
            hidden_urls = {item["url"] for item in self._state["hidden"]}
            pool = [item for item in self._items if item["url"] not in hidden_urls]
        elif self._tab == "saved":
            pool = list(self._state["saved"])
        else:
            pool = list(self._state["hidden"])
        if self._source_filter != "all":
            pool = [item for item in pool if item.get("source") == self._source_filter]
        if self._search:
            pool = [
                item for item in pool
                if self._search in " ".join(
                    (item.get("title", ""), item.get("category", ""), item.get("source", ""))
                ).lower()
            ]
        return pool

    def _prepare_item(self, item):
        prepared = dict(item)
        prepared["show_thumb"] = self.thumb_check.isChecked()
        saved_urls = {entry["url"] for entry in self._state["saved"]}
        prepared["saved"] = prepared["url"] in saved_urls
        if prepared.get("show_thumb") and prepared.get("pixmap") is None:
            prepared["pixmap"] = common.pixmap_from_cache(prepared.get("image"))
        return prepared

    def _status_text(self, count):
        if self._tab == "saved":
            text = f"{count} salvas"
        elif self._tab == "hidden":
            text = f"{count} ocultas"
        else:
            text = f"{count} notícias"
        if self._search:
            text += " · busca"
        return text

    def _render(self):
        self._clear_cards()
        visible = self._visible_items()
        seen_urls = set(self._state["seen"])

        if not visible:
            label = QLabel("Nada por aqui.")
            label.setObjectName("emptyLabel")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.list_layout.insertWidget(0, label)
            self.status.setText(self._status_text(0))
            return

        if self._tab == "feed" and self._source_filter == "all" and not self._search:
            head = self._prepare_item(visible[0])
            featured = FeaturedCard(head)
            featured.clicked.connect(self._open_url)
            featured.save_requested.connect(self._toggle_save)
            featured.hide_requested.connect(self._hide_item)
            featured.hovered.connect(self._on_hover)
            featured.set_seen(head["url"] in seen_urls)
            self._cards[head["url"]] = featured
            self.list_layout.insertWidget(self.list_layout.count() - 1, featured)
            rest = visible[1:]
        else:
            rest = visible

        for item in rest:
            prepared = self._prepare_item(item)
            card = NewsCard(prepared, restore_mode=(self._tab == "hidden"))
            card.clicked.connect(self._open_url)
            card.save_requested.connect(self._toggle_save)
            card.hide_requested.connect(self._hide_item)
            card.restore_requested.connect(self._restore_item)
            card.hovered.connect(self._on_hover)
            card.set_seen(prepared["url"] in seen_urls)
            self._cards[prepared["url"]] = card
            self.list_layout.insertWidget(self.list_layout.count() - 1, card)

        self.status.setText(self._status_text(len(visible)))

    def _find_item(self, url):
        for item in self._items:
            if item.get("url") == url:
                return item
        for item in self._state["saved"] + self._state["hidden"]:
            if item.get("url") == url:
                return item
        return None

    def _toggle_save(self, url):
        saved_urls = {entry["url"] for entry in self._state["saved"]}
        if url in saved_urls:
            self._state["saved"] = [entry for entry in self._state["saved"] if entry["url"] != url]
        else:
            item = self._find_item(url)
            if item is None:
                return
            snapshot = _as_snapshot(item)
            self._state["saved"] = [
                snapshot,
                *(entry for entry in self._state["saved"] if entry["url"] != url),
            ][:100]
        _save_state(self._state)
        self._render()

    def _hide_item(self, url):
        item = self._find_item(url)
        if item is None:
            return
        self._state["hidden"] = [
            *(entry for entry in self._state["hidden"] if entry["url"] != url),
            _as_snapshot(item),
        ]
        _save_state(self._state)

        def undo():
            self._state["hidden"] = [entry for entry in self._state["hidden"] if entry["url"] != url]
            _save_state(self._state)
            self._render()

        self._show_undo("Notícia ocultada", undo)
        self._render()

    def _restore_item(self, url):
        self._state["hidden"] = [entry for entry in self._state["hidden"] if entry["url"] != url]
        _save_state(self._state)
        self._render()

    def _show_undo(self, message, on_undo):
        self._clear_undo()
        bar = QFrame()
        bar.setObjectName("undoBar")
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(10, 6, 6, 6)
        bar_layout.setSpacing(10)
        label = QLabel(message)
        bar_layout.addWidget(label)
        bar_layout.addStretch()
        undo_btn = QPushButton("Desfazer")
        undo_btn.setObjectName("secondaryBtn")
        undo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        undo_btn.clicked.connect(on_undo)
        bar_layout.addWidget(undo_btn)
        self.list_layout.insertWidget(0, bar)
        self._undo_bar = bar
        self._undo_timer = QTimer(self)
        self._undo_timer.setSingleShot(True)
        self._undo_timer.timeout.connect(bar.deleteLater)
        self._undo_timer.start(6000)

    def _open_url(self, url):
        if url not in self._state["seen"]:
            self._state["seen"] = self._state["seen"] + [url]
            _save_state(self._state)
        card = self._cards.get(url)
        if card is not None:
            card.set_seen(True)
        QDesktopServices.openUrl(QUrl(url))

    def shutdown(self):
        if self._worker and self._worker.isRunning():
            self._worker.requestInterruption()
            if not self._worker.wait(2500):
                self._worker.terminate()
                self._worker.wait()
