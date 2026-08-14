"""Tema do Organizador Pessoal: estado + aplicação (fachada).

- Dados de cores → `theme_palette.py`
- Montagem do QSS → `stylesheet.py`
- Este módulo mantém o estado global e injeta a paleta ativa como variáveis
  de módulo (`theme.ACCENT`, `theme.BG`, …) para compatibilidade com o restante
  do código, além de aplicar fonte/palette/QSS/sombras na aplicação.
"""

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QGraphicsDropShadowEffect

import stylesheet
from theme_palette import (
    HIGH_CONTRAST_OVERRIDES,
    SHADOW_OBJECT_NAMES,
    THEMES,
    THUMB_HEIGHT,
    THUMB_WIDTH,
)

# Injetados em `apply_theme` a partir da paleta ativa (nomes de cor do módulo).
ACCENT = BG = TEXT = MUTED = None

CURRENT_THEME = "dark"
FONT_SIZE = 10
FONT_SCALE = 1.0
NOTIFY_TRAY = True
NOTIFY_SOUND = True
HIGH_CONTRAST = False

__all__ = [
    "CURRENT_THEME",
    "FONT_SIZE",
    "FONT_SCALE",
    "NOTIFY_TRAY",
    "NOTIFY_SOUND",
    "HIGH_CONTRAST",
    "THUMB_WIDTH",
    "THUMB_HEIGHT",
    "SHADOW_OBJECT_NAMES",
    "apply_theme",
    "apply_stylesheet",
    "apply_font_scale",
    "set_font_scale",
]


def _palette():
    """Paleta efetiva (tema ativo + overrides de alto contraste)."""
    pal = dict(THEMES[CURRENT_THEME])
    if HIGH_CONTRAST:
        pal.update(HIGH_CONTRAST_OVERRIDES)
    return pal


def apply_theme(app, name):
    """Aplica um tema ('dark'/'light') na aplicação e expõe as cores no módulo."""
    global CURRENT_THEME
    CURRENT_THEME = "dark" if name == "dark" else "light"
    globals().update(_palette())
    apply_stylesheet(app)


def apply_shadow_colors(app):
    for widget in app.allWidgets():
        if widget.objectName() in SHADOW_OBJECT_NAMES:
            effect = widget.graphicsEffect()
            if isinstance(effect, QGraphicsDropShadowEffect):
                effect.setColor(QColor(*SHADOW_COLOR))


def set_font_scale(scale):
    global FONT_SCALE
    FONT_SCALE = max(0.8, min(1.6, scale))


def apply_font_scale(app, scale):
    set_font_scale(scale)
    apply_stylesheet(app)


def apply_stylesheet(app):
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", max(6, round(FONT_SIZE * FONT_SCALE))))
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(BG))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Base, QColor(INPUT))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(CARD))
    palette.setColor(QPalette.ColorRole.Text, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Button, QColor(BTN))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(ACCENT))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(SURFACE))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(TEXT))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(PLACEHOLDER))
    palette.setColor(QPalette.ColorRole.Link, QColor(ACCENT))
    app.setPalette(palette)
    app.setStyleSheet(stylesheet.build_stylesheet(_palette(), FONT_SCALE))
    apply_shadow_colors(app)