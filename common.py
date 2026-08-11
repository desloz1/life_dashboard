import hashlib
import os
import time
from pathlib import Path

import qtawesome as qta
import requests
from PySide6.QtCore import QByteArray, QEasingCurve, QPropertyAnimation, Property, Qt
from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

import log
import scraper
import theme

logger = log.get_logger("life_dashboard.common")

CACHE_DIR = Path(__file__).resolve().parent / "cache" / "images"


def icon(name, color=None, size=22):
    return qta.icon(name, color=color or theme.ACCENT).pixmap(size, size)


def make_title(icon_name, text):
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(10)
    icon_label = QLabel()
    icon_label.setPixmap(icon(icon_name, theme.ACCENT, 22))
    label = QLabel(text)
    label.setObjectName("pageTitle")
    layout.addWidget(icon_label)
    layout.addWidget(label)
    return widget


def make_shadow(widget, x=0, y=3, blur=18):
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(x, y)
    widget.setGraphicsEffect(effect)
    return effect


def rounded_pixmap(pixmap, radius=10):
    rounded = QPixmap(pixmap.size())
    rounded.fill(Qt.GlobalColor.transparent)
    painter = QPainter(rounded)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(QRectF(pixmap.rect()), radius, radius)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, pixmap)
    painter.end()
    return rounded


def remove_shimmers(layout):
    for index in range(layout.count() - 1, -1, -1):
        item = layout.itemAt(index)
        widget = item.widget()
        if isinstance(widget, SkeletonShimmer):
            layout.takeAt(index)
            widget.deleteLater()


class SkeletonShimmer(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("skeleton")
        self._offset = -0.5
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(1200)
        self._anim.setStartValue(-0.5)
        self._anim.setEndValue(1.5)
        self._anim.setEasingCurve(QEasingCurve.InOutQuad)
        self._anim.setLoopCount(-1)
        self._anim.start()

    def getOffset(self):
        return self._offset

    def setOffset(self, value):
        self._offset = float(value)
        self.update()

    offset = Property(float, getOffset, setOffset)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        painter.fillRect(rect, QColor(theme.CARD))
        grad = QLinearGradient(rect.topLeft(), rect.topRight())
        pos = self._offset
        left = min(1.0, max(0.0, pos - 0.15))
        mid1 = min(1.0, max(0.0, pos - 0.02))
        mid2 = min(1.0, pos + 0.02)
        right = min(1.0, pos + 0.15)
        highlight = QColor(theme.ACCENT_SOFT) if theme.CURRENT_THEME == "light" else QColor(theme.THUMB_BG).lighter(120)
        grad.setColorAt(left, QColor(theme.CARD))
        grad.setColorAt(mid1, highlight)
        grad.setColorAt(mid2, highlight)
        grad.setColorAt(right, QColor(theme.CARD))
        painter.fillRect(rect, grad)
        painter.end()


def _cache_path(url):
    hasher = hashlib.sha1(url.encode("utf-8")).hexdigest()
    ext = os.path.splitext(url)[1].split("?")[0] or ".img"
    return CACHE_DIR / f"{hasher}{ext}"


def download_image_bytes(url):
    """Baixa bytes da imagem usando cache em disco. Thread-safe."""
    if not url:
        return None
    cache_path = _cache_path(url)
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        if cache_path.exists() and (time.time() - cache_path.stat().st_mtime) < 24 * 3600:
            return cache_path.read_bytes()
    except Exception as exc:
        logger.debug("Falha ao ler cache de imagem %s: %s", url, exc)
    try:
        response = requests.get(url, headers=scraper.HEADERS, timeout=10)
        if response.status_code != 200:
            return None
        data = response.content
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(data)
        except Exception as exc:
            logger.debug("Falha ao gravar cache de imagem %s: %s", url, exc)
        return data
    except requests.RequestException as exc:
        logger.warning("Falha ao baixar imagem %s: %s", url, exc)
        return None


def pixmap_from_bytes(data):
    """Constrói QPixmap escalado a partir de bytes. Chamar na thread da GUI."""
    if not data:
        return None
    pixmap = QPixmap()
    if not pixmap.loadFromData(QByteArray(data)):
        return None
    return pixmap.scaled(
        theme.THUMB_WIDTH,
        theme.THUMB_HEIGHT,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )


def cover_pixmap(pixmap, width, height):
    """Recorta o pixmap centralizado na proporção cover (sem distorção)."""
    if pixmap is None:
        return None
    scaled = pixmap.scaled(
        width,
        height,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    x = (scaled.width() - width) // 2
    y = (scaled.height() - height) // 2
    return scaled.copy(x, y, width, height)


def pixmap_from_cache(url):
    """Lê pixmap do cache local sem rede. Retorna None se ausente/corrompido."""
    if not url:
        return None
    path = _cache_path(url)
    try:
        if path.exists():
            pixmap = QPixmap()
            if pixmap.loadFromData(path.read_bytes()):
                return pixmap.scaled(
                    theme.THUMB_WIDTH,
                    theme.THUMB_HEIGHT,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
    except Exception as exc:
        logger.debug("Falha ao ler pixmap do cache %s: %s", url, exc)
    return None
