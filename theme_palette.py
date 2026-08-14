"""Paleta de cores e constantes visuais do Organizador Pessoal.

Somente dados (sem lógica). A aplicação efetiva acontece em `theme.py`
(estado + apply_*) e `stylesheet.py` (montagem do QSS).
"""

DARK_THEME = {
    "ACCENT": "#5b8cff",
    "ACCENT_HOVER": "#7aa2ff",
    "ACCENT_DARK": "#3f6ee0",
    "ACCENT_SOFT": "#2b3a5e",
    "BG": "#0f1115",
    "SURFACE": "#171a21",
    "CARD": "#1c2027",
    "CARD_HOVER": "#1f2430",
    "BORDER": "#262b35",
    "BORDER_HOVER": "#3b4a6e",
    "TEXT": "#e8ecf3",
    "MUTED": "#8a93a6",
    "DANGER": "#ff6b6b",
    "DANGER_SOFT": "#3a2328",
    "DANGER_HOVER": "#4a2a30",
    "WARN": "#f0a04b",
    "WARN_SOFT": "#3a2f1c",
    "OK": "#34c38f",
    "OK_SOFT": "#1f3a31",
    "BEVEL_LIGHT": "#394152",
    "BEVEL_DARK": "#0a0c10",
    "SHADOW_COLOR": (0, 0, 0, 150),
    "BTN": "#222837",
    "BTN_HOVER": "#2a3142",
    "BTN_PRESSED": "#1d2330",
    "BTN_DISABLED": "#20242e",
    "BTN_DISABLED_TEXT": "#5a6375",
    "INPUT": "#12151b",
    "TOGGLE_BTN": "#22314f",
    "TOGGLE_BTN_HOVER": "#2b3f66",
    "SECONDARY_BTN": "#232a36",
    "SECONDARY_BTN_HOVER": "#2c3442",
    "SIDEBAR_SELECTED": "#2b3a5e",
    "SIDEBAR_HOVER": "#232a36",
    "SIDEBAR_DISABLED": "#4a5262",
    "SCROLL_HANDLE": "#333c50",
    "SCROLL_HANDLE_HOVER": "#414c66",
    "THUMB_BG": "#222834",
    "PAUSED_BG": "#191c22",
    "PAUSED_BORDER": "#2a2f3a",
    "PLACEHOLDER": "#5a6375",
}

LIGHT_THEME = {
    "ACCENT": "#1a73e8",
    "ACCENT_HOVER": "#1557b0",
    "ACCENT_DARK": "#0d5cb8",
    "ACCENT_SOFT": "#e3f0fd",
    "BG": "#f4f6f9",
    "SURFACE": "#ffffff",
    "CARD": "#ffffff",
    "CARD_HOVER": "#fbfdff",
    "BORDER": "#e2e6ec",
    "BORDER_HOVER": "#aecdf5",
    "TEXT": "#1a1f2b",
    "MUTED": "#5f6b7a",
    "DANGER": "#d93025",
    "DANGER_SOFT": "#fdecea",
    "DANGER_HOVER": "#f8d7d5",
    "WARN": "#b26a00",
    "WARN_SOFT": "#fdf3e3",
    "OK": "#1e8e5a",
    "OK_SOFT": "#e2f6ee",
    "BEVEL_LIGHT": "#ffffff",
    "BEVEL_DARK": "#c6cfda",
    "SHADOW_COLOR": (45, 63, 92, 60),
    "BTN": "#eef1f5",
    "BTN_HOVER": "#e3e8ef",
    "BTN_PRESSED": "#d8dee7",
    "BTN_DISABLED": "#eceef2",
    "BTN_DISABLED_TEXT": "#a0a8b5",
    "INPUT": "#ffffff",
    "TOGGLE_BTN": "#e3f0fd",
    "TOGGLE_BTN_HOVER": "#cfe3fb",
    "SECONDARY_BTN": "#eef1f5",
    "SECONDARY_BTN_HOVER": "#e3e8ef",
    "SIDEBAR_SELECTED": "#e3f0fd",
    "SIDEBAR_HOVER": "#f0f4f8",
    "SIDEBAR_DISABLED": "#b6bdc9",
    "SCROLL_HANDLE": "#c3cbd8",
    "SCROLL_HANDLE_HOVER": "#a9b4c4",
    "THUMB_BG": "#eef1f4",
    "PAUSED_BG": "#f7f8fa",
    "PAUSED_BORDER": "#e6e9ee",
    "PLACEHOLDER": "#9aa4b2",
}

THEMES = {"dark": DARK_THEME, "light": LIGHT_THEME}

# Paleta de alto contraste (aplicada por cima da paleta ativa em theme.py).
HIGH_CONTRAST_OVERRIDES = {
    "ACCENT": "#ffd60a",
    "BG": "#050505",
    "SURFACE": "#0c0c0c",
    "CARD": "#111111",
    "BORDER": "#2b2b2b",
    "TEXT": "#ffffff",
    "MUTED": "#cfcfcf",
}

THUMB_WIDTH = 130
THUMB_HEIGHT = 90

SHADOW_OBJECT_NAMES = ("sidebar", "newsCard", "featuredCard", "reminderCard", "weatherCard", "dayCard", "dashCard", "dashStats", "taskCard", "noteCard", "prodCard", "webcamCard")