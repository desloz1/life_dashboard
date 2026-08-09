import re

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QGraphicsDropShadowEffect

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

CURRENT_THEME = "dark"
FONT_SIZE = 10
FONT_SCALE = 1.0
NOTIFY_TRAY = True
NOTIFY_SOUND = True
HIGH_CONTRAST = False

THUMB_WIDTH = 130
THUMB_HEIGHT = 90

SHADOW_OBJECT_NAMES = ("sidebar", "newsCard", "featuredCard", "reminderCard", "weatherCard", "dayCard", "dashCard", "taskCard")


def apply_theme(app, name):
    global CURRENT_THEME
    CURRENT_THEME = "dark" if name == "dark" else "light"
    globals().update(THEMES[CURRENT_THEME])
    if HIGH_CONTRAST:
        globals().update({
            "ACCENT": "#ffd60a",
            "BG": "#050505",
            "SURFACE": "#0c0c0c",
            "CARD": "#111111",
            "BORDER": "#2b2b2b",
            "TEXT": "#ffffff",
            "MUTED": "#cfcfcf",
        })
    apply_stylesheet(app)


def apply_shadow_colors(app):
    for widget in app.allWidgets():
        if widget.objectName() in SHADOW_OBJECT_NAMES:
            effect = widget.graphicsEffect()
            if isinstance(effect, QGraphicsDropShadowEffect):
                effect.setColor(QColor(*SHADOW_COLOR))


def _scale_font_sizes(sheet):
    if FONT_SCALE == 1.0:
        return sheet
    return re.sub(
        r"font-size:\s*([\d.]+)px",
        lambda m: f"font-size: {max(6, round(float(m.group(1)) * FONT_SCALE))}px",
        sheet,
    )


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
    sheet = f"""
        * {{
            font-family: "Segoe UI";
            outline: none;
        }}
        QMainWindow, QDialog, QMessageBox {{
            background: {BG};
        }}
        QToolTip {{
            background: {SURFACE};
            color: {TEXT};
            border: 1px solid {BORDER};
            border-radius: 6px;
            padding: 6px 10px;
        }}

        #sidebar {{
            background: {SURFACE};
            border-radius: 16px;
            margin: 8px 0 8px 8px;
        }}
        #sidebarBtn {{
            background: transparent;
            border: none;
            border-radius: 12px;
            font-size: 14px;
        }}
        #sidebarBtn:hover {{
            background: {SIDEBAR_HOVER};
        }}
        #sidebarBtn:checked {{
            background: {SIDEBAR_SELECTED};
        }}
        #sidebarBtn:checked:hover {{
            background: {SIDEBAR_SELECTED};
        }}
        #sidebarBtn:disabled {{
            color: {SIDEBAR_DISABLED};
        }}

        #themeBtn, #settingsBtn {{
            background: transparent;
            border: none;
            border-radius: 12px;
            padding: 8px;
        }}
        #themeBtn:hover, #settingsBtn:hover {{
            background: {SIDEBAR_HOVER};
        }}
        #sidebarSep {{
            background: {BORDER};
            margin: 4px 10px;
            border: none;
        }}

        #pageTitle {{
            font-size: 20px;
            font-weight: 700;
            color: {TEXT};
        }}
        #status {{
            color: {MUTED};
            font-size: 12px;
        }}

        QPushButton {{
            background: {BTN};
            color: {TEXT};
            border: 1px solid {BORDER};
            border-top: 1px solid {BEVEL_LIGHT};
            border-bottom: 2px solid {BEVEL_DARK};
            border-radius: 8px;
            padding: 7px 14px;
            font-size: 13px;
            font-weight: 600;
        }}
        QPushButton:hover {{ background: {BTN_HOVER}; }}
        QPushButton:pressed {{
            background: {BTN_PRESSED};
            border-top: 2px solid {BEVEL_DARK};
            border-bottom: 1px solid {BEVEL_LIGHT};
        }}
        QPushButton:disabled {{ background: {BTN_DISABLED}; color: {BTN_DISABLED_TEXT}; border-color: {BORDER}; }}

        #refreshBtn {{
            background: {ACCENT};
            color: #ffffff;
            border: none;
            border-bottom: 2px solid {ACCENT_DARK};
        }}
        #refreshBtn:hover {{ background: {ACCENT_HOVER}; }}
        #refreshBtn:pressed {{
            border-top: 2px solid {ACCENT_DARK};
            border-bottom: none;
        }}
        #refreshBtn:disabled {{ background: {BTN_DISABLED}; color: {BTN_DISABLED_TEXT}; }}

        #toggleBtn {{
            background: {TOGGLE_BTN};
            color: {ACCENT};
            border: none;
            padding: 6px 12px;
            font-size: 12px;
        }}
        #toggleBtn:hover {{ background: {TOGGLE_BTN_HOVER}; }}
        #secondaryBtn {{
            background: {SECONDARY_BTN};
            color: {TEXT};
            border: none;
            padding: 6px 12px;
            font-size: 12px;
        }}
        #secondaryBtn:hover {{ background: {SECONDARY_BTN_HOVER}; }}
        #dangerBtn {{
            background: {DANGER_SOFT};
            color: {DANGER};
            border: none;
            padding: 6px 12px;
            font-size: 12px;
        }}
        #dangerBtn:hover {{ background: {DANGER_HOVER}; }}

        #scrollArea, #hourScroll {{
            border: none;
            background: transparent;
        }}
        QScrollArea > QWidget > QWidget {{
            background: transparent;
        }}
        QScrollBar:vertical {{
            background: transparent;
            width: 10px;
            margin: 2px;
        }}
        QScrollBar::handle:vertical {{
            background: {SCROLL_HANDLE};
            border-radius: 4px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{ background: {SCROLL_HANDLE_HOVER}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: transparent;
        }}

        #newsCard, #reminderCard {{
            background: {CARD};
            border: 1px solid {BORDER};
            border-radius: 12px;
        }}
        #newsCard:hover {{
            border: 1px solid {BORDER_HOVER};
            background: {CARD_HOVER};
        }}
        #reminderCard[paused="true"] {{
            background: {PAUSED_BG};
            border: 1px solid {PAUSED_BORDER};
        }}
        #reminderCard[overdue="true"] {{
            background: {DANGER_SOFT};
            border: 1px solid {DANGER};
        }}
        #notifPopup {{
            background: {SURFACE};
            border: 1px solid {BORDER};
            border-radius: 12px;
        }}
        #notifTitle {{
            font-size: 14px;
            font-weight: 700;
            color: {TEXT};
        }}
        #notifMsg {{
            font-size: 13px;
            color: {MUTED};
        }}
        #dashGreeting {{
            font-size: 26px;
            font-weight: 800;
            color: {TEXT};
        }}
        #dashDate {{
            font-size: 14px;
            color: {MUTED};
        }}
        #dashCard {{
            background: {CARD};
            border: 1px solid {BORDER};
            border-radius: 14px;
        }}
        #dashCard:hover {{
            border: 1px solid {BORDER_HOVER};
            background: {CARD_HOVER};
        }}
        #dashCardTitle {{
            font-size: 13px;
            font-weight: 700;
            color: {MUTED};
        }}
        #dashCardValue {{
            font-size: 18px;
            font-weight: 800;
            color: {TEXT};
        }}
        #dashCardSub {{
            font-size: 12px;
            color: {MUTED};
        }}
        #dashLink {{
            color: {ACCENT};
            font-size: 15px;
            font-weight: 700;
        }}
        #dashAction {{
            background: {SECONDARY_BTN};
            color: {TEXT};
            border: none;
            padding: 9px 16px;
            font-size: 13px;
            font-weight: 600;
            border-radius: 10px;
        }}
        #dashAction:hover {{ background: {SECONDARY_BTN_HOVER}; }}
        #dashAction QToolButton, #dashAction QLabel {{ color: {TEXT}; }}

        QProgressBar {{
            background: {BTN};
            border: 1px solid {BORDER};
            border-radius: 8px;
            height: 14px;
            text-align: center;
            font-size: 11px;
            font-weight: 700;
            color: {TEXT};
        }}
        QProgressBar::chunk {{
            background: {ACCENT};
            border-radius: 7px;
        }}

        #taskCard {{
            background: {CARD};
            border: 1px solid {BORDER};
            border-radius: 12px;
        }}
        #taskCard:hover {{
            border: 1px solid {BORDER_HOVER};
            background: {CARD_HOVER};
        }}
        #taskCard[completed="true"] {{
            background: {PAUSED_BG};
            border: 1px solid {PAUSED_BORDER};
        }}
        #taskCard[completed="true"] #taskTitle {{
            color: {MUTED};
        }}
        #taskCard[completed="true"] #taskMeta {{
            color: {MUTED};
        }}
        #taskCheck {{
            spacing: 10px;
        }}
        #taskCheck::indicator {{
            width: 20px;
            height: 20px;
            border: 2px solid {BORDER};
            border-radius: 6px;
            background: {INPUT};
        }}
        #taskCheck::indicator:hover {{ border: 2px solid {BORDER_HOVER}; }}
        #taskCheck::indicator:checked {{
            background: {ACCENT};
            border-color: {ACCENT};
        }}
        #taskTitle {{
            font-size: 14px;
            font-weight: 600;
            color: {TEXT};
        }}
        #taskMeta {{
            font-size: 12px;
            color: {MUTED};
        }}
        #prioBadge {{
            font-size: 11px;
            font-weight: 700;
            border-radius: 6px;
            padding: 2px 8px;
        }}
        #prioBadge[level="alta"] {{ background: {DANGER_SOFT}; color: {DANGER}; }}
        #prioBadge[level="media"] {{ background: {WARN_SOFT}; color: {WARN}; }}
        #prioBadge[level="baixa"] {{ background: {OK_SOFT}; color: {OK}; }}
        #catBadge {{
            color: {MUTED};
            font-size: 11px;
            font-weight: 600;
            background: {BTN};
            border: 1px solid {BORDER};
            border-radius: 6px;
            padding: 2px 8px;
        }}
        #dueBadge {{
            font-size: 11px;
            font-weight: 700;
            border-radius: 6px;
            padding: 2px 8px;
        }}
        #dueBadge[state="overdue"] {{ background: {DANGER_SOFT}; color: {DANGER}; }}
        #dueBadge[state="today"] {{ background: {ACCENT_SOFT}; color: {ACCENT}; }}
        #dueBadge[state="tomorrow"] {{ background: {OK_SOFT}; color: {OK}; }}
        #dueBadge[state="future"] {{ background: {BTN}; color: {MUTED}; }}
        #filterBtn {{
            background: transparent;
            color: {MUTED};
            border: none;
            border-radius: 8px;
            padding: 5px 12px;
            font-size: 12px;
            font-weight: 600;
        }}
        #filterBtn:hover {{ background: {BTN_HOVER}; color: {TEXT}; }}
        #filterBtn:checked {{ background: {ACCENT_SOFT}; color: {ACCENT}; }}

        #agendaRow {{
            background: {CARD};
            border: 1px solid {BORDER};
            border-radius: 10px;
        }}
        #agendaRow:hover {{
            border: 1px solid {BORDER_HOVER};
            background: {CARD_HOVER};
        }}
        #agendaRow[completed="true"] {{
            background: {PAUSED_BG};
            border: 1px solid {PAUSED_BORDER};
        }}
        #agendaRow[completed="true"] #taskTitle {{ color: {MUTED}; }}
        #dayHeader {{
            font-size: 13px;
            font-weight: 800;
            color: {ACCENT};
            padding: 4px 0;
        }}
        #calCell {{
            background: {CARD};
            border: 1px solid {BORDER};
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            color: {TEXT};
            padding: 2px;
        }}
        #calCell:hover {{
            border: 1px solid {BORDER_HOVER};
            background: {CARD_HOVER};
        }}
        #calCell[today="true"] {{
            border: 1px solid {ACCENT};
            color: {ACCENT};
        }}
        #calCell[selected="true"] {{
            background: {ACCENT};
            border: 1px solid {ACCENT};
            color: #ffffff;
        }}
        #calCell[empty="true"] {{
            background: transparent;
            border: none;
        }}
        #calTitle {{
            font-size: 14px;
            font-weight: 800;
            color: {TEXT};
        }}
        #weekCol {{
            background: {CARD};
            border: 1px solid {BORDER};
            border-radius: 10px;
        }}
        #weekColHead {{
            font-size: 13px;
            font-weight: 700;
            color: {MUTED};
        }}
        #weekColHead[today="true"] {{
            color: {ACCENT};
        }}
        #navBtn {{
            background: {BTN};
            color: {TEXT};
            border: 1px solid {BORDER};
            border-radius: 8px;
            padding: 4px 10px;
            font-size: 13px;
        }}
        #navBtn:hover {{ background: {BTN_HOVER}; }}

        #weatherCard, #dayCard {{
            background: {CARD};
            border: 1px solid {BORDER};
            border-radius: 12px;
        }}
        #clockTime {{
            font-size: 52px;
            font-weight: 700;
            color: {TEXT};
            letter-spacing: 2px;
        }}
        #clockDate {{
            font-size: 16px;
            color: {MUTED};
        }}
        #weatherTemp {{
            font-size: 44px;
            font-weight: 700;
            color: {TEXT};
        }}
        #weatherDesc {{
            font-size: 17px;
            font-weight: 600;
            color: {TEXT};
        }}
        #weatherMeta {{
            font-size: 13px;
            color: {MUTED};
        }}
        #dayCardDay {{
            font-size: 13px;
            font-weight: 700;
            color: {ACCENT};
            text-transform: uppercase;
        }}
        #dayCardDate {{
            font-size: 11px;
            color: {MUTED};
        }}
        #dayCardTemp {{
            font-size: 15px;
            font-weight: 700;
            color: {TEXT};
        }}
        #dayCardPrecip {{
            font-size: 11px;
            color: {MUTED};
        }}
        #hourCard {{
            background: {CARD};
            border: 1px solid {BORDER};
            border-radius: 12px;
        }}
        #hourCard:hover {{ border: 1px solid {BORDER_HOVER}; }}
        #hourLabel {{
            font-size: 12px;
            font-weight: 700;
            color: {ACCENT};
        }}
        #hourTemp {{
            font-size: 15px;
            font-weight: 700;
            color: {TEXT};
        }}
        #metricChip {{
            background: {BTN};
            border: 1px solid {BORDER};
            border-radius: 10px;
        }}
        #metricValue {{
            font-size: 14px;
            font-weight: 700;
            color: {TEXT};
        }}
        #metricLabel {{
            font-size: 11px;
            color: {MUTED};
        }}
        #newsThumb {{
            background: {THUMB_BG};
            border-radius: 10px;
        }}
        #newsCategory {{
            color: {ACCENT};
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
        }}
        #newsDate {{
            color: {MUTED};
            font-size: 12px;
        }}
        #newsSource {{
            color: {MUTED};
            font-size: 11px;
            font-weight: 600;
            background: {BTN};
            border: 1px solid {BORDER};
            border-radius: 6px;
            padding: 1px 8px;
        }}
        #newsTitle {{
            font-size: 14px;
            font-weight: 600;
            color: {TEXT};
        }}
        #newsTime {{
            color: {MUTED};
            font-size: 12px;
        }}
        #newsCard[seen="true"], #featuredCard[seen="true"] {{
            background: {PAUSED_BG};
            border: 1px solid {PAUSED_BORDER};
        }}
        #newsCard[seen="true"] #newsTitle, #featuredCard[seen="true"] #featuredTitle {{
            color: {MUTED};
        }}
        #cardBtn {{
            background: transparent;
            border: none;
            border-radius: 8px;
        }}
        #cardBtn:hover {{ background: {BTN_HOVER}; }}

        #featuredCard {{
            background: {CARD};
            border: 1px solid {BORDER};
            border-radius: 16px;
        }}
        #featuredCard:hover {{
            border: 1px solid {BORDER_HOVER};
            background: {CARD_HOVER};
        }}
        #featuredTitle {{
            font-size: 19px;
            font-weight: 700;
            color: {TEXT};
        }}
        #featuredThumb {{
            background: {THUMB_BG};
            border-radius: 12px;
        }}

        #tabBtn {{
            background: transparent;
            color: {MUTED};
            border: none;
            border-radius: 8px;
            padding: 6px 14px;
            font-size: 13px;
            font-weight: 600;
        }}
        #tabBtn:hover {{ background: {BTN_HOVER}; color: {TEXT}; }}
        #tabBtn:checked {{ background: {ACCENT_SOFT}; color: {ACCENT}; }}

        #sourceBtn {{
            background: {BTN};
            color: {MUTED};
            border: 1px solid {BORDER};
            border-radius: 999px;
            padding: 4px 12px;
            font-size: 12px;
            font-weight: 600;
        }}
        #sourceBtn:hover {{ color: {TEXT}; border-color: {BORDER_HOVER}; }}
        #sourceBtn:checked {{ background: {ACCENT}; color: #ffffff; border-color: {ACCENT}; }}

        #newsSearch {{
            background: {INPUT};
            border: 1px solid {BORDER};
            border-radius: 999px;
            padding: 6px 14px;
            font-size: 13px;
        }}
        #newsSearch:focus {{ border: 1px solid {ACCENT}; }}

        #emptyLabel {{
            color: {MUTED};
            font-size: 14px;
            padding: 40px;
        }}
        #undoBar {{
            background: {ACCENT_SOFT};
            border: 1px solid {BORDER};
            border-radius: 10px;
            padding: 6px 10px;
        }}
        #undoBar QLabel {{ color: {TEXT}; font-size: 13px; }}
        #errorLabel {{
            color: {DANGER};
            font-size: 14px;
            padding: 30px;
            background: {CARD};
            border: 1px solid {DANGER_SOFT};
            border-radius: 12px;
        }}
        #reminderIcon {{
            font-size: 24px;
            min-width: 40px;
        }}
        #reminderTitle {{
            font-size: 15px;
            font-weight: 700;
            color: {TEXT};
        }}
        #reminderDesc {{
            font-size: 13px;
            color: {MUTED};
        }}
        #reminderSchedule {{
            font-size: 12px;
            font-weight: 700;
            color: {ACCENT};
        }}
        #reminderNext {{
            font-size: 12px;
            color: {MUTED};
        }}

        QLineEdit, QTimeEdit, QDateEdit, QSpinBox, QComboBox {{
            padding: 8px 10px;
            border: 1px solid {BORDER};
            border-radius: 8px;
            background: {INPUT};
            color: {TEXT};
            font-size: 13px;
            selection-background-color: {ACCENT};
        }}
        QLineEdit:focus, QTimeEdit:focus, QDateEdit:focus, QSpinBox:focus, QComboBox:focus {{
            border: 1px solid {ACCENT};
        }}
        QLineEdit::placeholder {{ color: {PLACEHOLDER}; }}
        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}
        QComboBox QAbstractItemView {{
            background: {SURFACE};
            color: {TEXT};
            border: 1px solid {BORDER};
            border-radius: 8px;
            selection-background-color: {SIDEBAR_SELECTED};
            padding: 4px;
        }}
        QCheckBox {{
            color: {TEXT};
            font-size: 13px;
            spacing: 8px;
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {BORDER};
            border-radius: 4px;
            background: {INPUT};
        }}
        QCheckBox::indicator:checked {{
            background: {ACCENT};
            border-color: {ACCENT};
        }}
        QTimeEdit::up-button, QTimeEdit::down-button,
        QSpinBox::up-button, QSpinBox::down-button,
        QDateEdit::up-button, QDateEdit::down-button {{
            background: transparent;
            border: none;
            width: 16px;
        }}
        QCalendarWidget QWidget {{
            background: {SURFACE};
            color: {TEXT};
        }}
        QCalendarWidget QAbstractItemView {{
            background: {SURFACE};
            color: {TEXT};
            selection-background-color: {ACCENT};
            selection-color: #ffffff;
        }}
        QCalendarWidget QToolButton {{
            background: transparent;
            border: none;
            border-radius: 6px;
            color: {TEXT};
            padding: 4px 8px;
        }}
        QDialogButtonBox QPushButton {{
            min-width: 84px;
        }}
        QMessageBox QLabel {{
            color: {TEXT};
        }}
    """
    app.setStyleSheet(_scale_font_sizes(sheet))
    apply_shadow_colors(app)
