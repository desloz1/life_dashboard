"""Folha de estilos (QSS) construída a partir de uma paleta de cores.

O template usa apenas as cores da paleta (chaves {P['NOME']}) e é resolvido
em `build_stylesheet`. CSS é separado da paleta e do tema (theme.py) para
manter cada responsabilidade em seu módulo.
"""

import re


def _scale_font_sizes(sheet, font_scale):
    if font_scale == 1.0:
        return sheet
    return re.sub(
        r"font-size:\s*([\d.]+)px",
        lambda mm: f"font-size: {max(6, round(float(mm.group(1)) * font_scale))}px",
        sheet,
    )


def build_stylesheet(palette, font_scale=1.0):
    """Monta o QSS a partir de um dict de cores (`P`) e do zoom de fonte."""
    P = palette
    sheet = f"""

        * {{
            font-family: "Segoe UI";
            outline: none;
        }}
        QMainWindow, QDialog, QMessageBox {{
            background: {P['BG']};
        }}
        QToolTip {{
            background: {P['SURFACE']};
            color: {P['TEXT']};
            border: 1px solid {P['BORDER']};
            border-radius: 6px;
            padding: 6px 10px;
        }}

        #sidebar {{
            background: {P['SURFACE']};
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
            background: {P['SIDEBAR_HOVER']};
        }}
        #sidebarBtn:checked {{
            background: {P['SIDEBAR_SELECTED']};
        }}
        #sidebarBtn:checked:hover {{
            background: {P['SIDEBAR_SELECTED']};
        }}
        #sidebarBtn:disabled {{
            color: {P['SIDEBAR_DISABLED']};
        }}

        #themeBtn, #settingsBtn {{
            background: transparent;
            border: none;
            border-radius: 12px;
            padding: 8px;
        }}
        #themeBtn:hover, #settingsBtn:hover {{
            background: {P['SIDEBAR_HOVER']};
        }}
        #sidebarSearchBtn {{
            background: transparent;
            border: none;
            border-radius: 12px;
            padding: 8px;
        }}
        #sidebarSearchBtn:hover {{
            background: {P['SIDEBAR_HOVER']};
        }}
        #sidebarSearchBtn:pressed {{
            background: {P['SIDEBAR_SELECTED']};
        }}
        #sidebarSep {{
            background: {P['BORDER']};
            margin: 4px 10px;
            border: none;
        }}

        #pageTitle {{
            font-size: 20px;
            font-weight: 700;
            color: {P['TEXT']};
        }}
        #status {{
            color: {P['MUTED']};
            font-size: 12px;
        }}

        QPushButton {{
            background: {P['BTN']};
            color: {P['TEXT']};
            border: 1px solid {P['BORDER']};
            border-top: 1px solid {P['BEVEL_LIGHT']};
            border-bottom: 2px solid {P['BEVEL_DARK']};
            border-radius: 8px;
            padding: 7px 14px;
            font-size: 13px;
            font-weight: 600;
        }}
        QPushButton:hover {{ background: {P['BTN_HOVER']}; }}
        QPushButton:pressed {{
            background: {P['BTN_PRESSED']};
            border-top: 2px solid {P['BEVEL_DARK']};
            border-bottom: 1px solid {P['BEVEL_LIGHT']};
        }}
        QPushButton:disabled {{ background: {P['BTN_DISABLED']}; color: {P['BTN_DISABLED_TEXT']}; border-color: {P['BORDER']}; }}

        #refreshBtn {{
            background: {P['ACCENT']};
            color: #ffffff;
            border: none;
            border-bottom: 2px solid {P['ACCENT_DARK']};
        }}
        #refreshBtn:hover {{ background: {P['ACCENT_HOVER']}; }}
        #refreshBtn:pressed {{
            border-top: 2px solid {P['ACCENT_DARK']};
            border-bottom: none;
        }}
        #refreshBtn:disabled {{ background: {P['BTN_DISABLED']}; color: {P['BTN_DISABLED_TEXT']}; }}

        #toggleBtn {{
            background: {P['TOGGLE_BTN']};
            color: {P['ACCENT']};
            border: none;
            padding: 6px 12px;
            font-size: 12px;
        }}
        #toggleBtn:hover {{ background: {P['TOGGLE_BTN_HOVER']}; }}
        #secondaryBtn {{
            background: {P['SECONDARY_BTN']};
            color: {P['TEXT']};
            border: none;
            padding: 6px 12px;
            font-size: 12px;
        }}
        #secondaryBtn:hover {{ background: {P['SECONDARY_BTN_HOVER']}; }}
        #dangerBtn {{
            background: {P['DANGER_SOFT']};
            color: {P['DANGER']};
            border: none;
            padding: 6px 12px;
            font-size: 12px;
        }}
        #dangerBtn:hover {{ background: {P['DANGER_HOVER']}; }}

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
            background: {P['SCROLL_HANDLE']};
            border-radius: 4px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{ background: {P['SCROLL_HANDLE_HOVER']}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: transparent;
        }}

        #newsCard, #reminderCard {{
            background: {P['CARD']};
            border: 1px solid {P['BORDER']};
            border-radius: 12px;
        }}
        #newsCard:hover {{
            border: 1px solid {P['BORDER_HOVER']};
            background: {P['CARD_HOVER']};
        }}
        #reminderCard[paused="true"] {{
            background: {P['PAUSED_BG']};
            border: 1px solid {P['PAUSED_BORDER']};
        }}
        #reminderCard[overdue="true"] {{
            background: {P['DANGER_SOFT']};
            border: 1px solid {P['DANGER']};
        }}
        #reminderCard[done="true"] {{
            background: {P['OK_SOFT']};
            border: 1px solid {P['OK']};
        }}
        #reminderCard[done="true"] #reminderTitle {{
            color: {P['OK']};
            text-decoration: line-through;
        }}
        #reminderCard[done="true"] #reminderMeta {{
            color: {P['OK']};
        }}
        #notifPopup {{
            background: {P['SURFACE']};
            border: 1px solid {P['BORDER']};
            border-radius: 12px;
        }}
        #notifTitle {{
            font-size: 14px;
            font-weight: 700;
            color: {P['TEXT']};
        }}
        #notifMsg {{
            font-size: 13px;
            color: {P['MUTED']};
        }}
        #dashGreeting {{
            font-size: 26px;
            font-weight: 800;
            color: {P['TEXT']};
        }}
        #dashDate {{
            font-size: 14px;
            color: {P['MUTED']};
        }}
        #dashCard {{
            background: {P['CARD']};
            border: 1px solid {P['BORDER']};
            border-radius: 14px;
        }}
        #dashCard:hover {{
            border: 1px solid {P['BORDER_HOVER']};
            background: {P['CARD_HOVER']};
        }}
        #dashCardTitle {{
            font-size: 13px;
            font-weight: 700;
            color: {P['MUTED']};
        }}
        #dashCardValue {{
            font-size: 18px;
            font-weight: 800;
            color: {P['TEXT']};
        }}
        #dashCardSub {{
            font-size: 12px;
            color: {P['MUTED']};
        }}
        #dashLink {{
            color: {P['ACCENT']};
            font-size: 15px;
            font-weight: 700;
        }}
        #dashToday {{
            background: {P['CARD']};
            border: 1px solid {P['BORDER']};
            border-radius: 14px;
        }}
        #dashTodayTitle {{
            font-size: 15px;
            font-weight: 700;
            color: {P['TEXT']};
        }}
        #dashTodayIcon {{
            min-width: 26px;
        }}
        #dashTodayTemp {{
            font-size: 22px;
            font-weight: 800;
            color: {P['TEXT']};
        }}
        #dashTodaySub {{
            font-size: 12px;
            color: {P['MUTED']};
        }}
        #dashTodayItem {{
            font-size: 13px;
            font-weight: 600;
            color: {P['TEXT']};
        }}
        #dashAction {{
            background: {P['SECONDARY_BTN']};
            color: {P['TEXT']};
            border: none;
            padding: 9px 16px;
            font-size: 13px;
            font-weight: 600;
            border-radius: 10px;
        }}
        #dashAction:hover {{ background: {P['SECONDARY_BTN_HOVER']}; }}
        #dashAction QToolButton, #dashAction QLabel {{ color: {P['TEXT']}; }}

        #dashNewsHeader {{
            font-size: 15px;
            font-weight: 700;
            color: {P['TEXT']};
        }}
        #dashStats {{
            background: {P['CARD']};
            border: 1px solid {P['BORDER']};
            border-radius: 14px;
        }}
        #dashStatsTitle {{
            font-size: 15px;
            font-weight: 700;
            color: {P['TEXT']};
        }}
        #streakValue {{
            font-size: 22px;
            font-weight: 800;
            color: {P['WARN']};
        }}
        #streakLabel {{
            font-size: 12px;
            color: {P['MUTED']};
        }}
        #weekTotal {{
            font-size: 13px;
            font-weight: 600;
            color: {P['TEXT']};
        }}
        #dashCatName {{
            font-size: 12px;
            font-weight: 600;
            color: {P['TEXT']};
        }}
        #dashCatPct {{
            font-size: 11px;
            color: {P['MUTED']};
        }}
        #dashStatsEmpty {{
            color: {P['MUTED']};
            font-size: 12px;
        }}
        #catBar {{
            background: {P['BTN']};
            border: 1px solid {P['BORDER']};
            border-radius: 6px;
        }}
        #catBar::chunk {{
            background: {P['ACCENT']};
            border-radius: 5px;
        }}
        #dashNewsRow {{
            background: {P['CARD']};
            border: 1px solid {P['BORDER']};
            border-radius: 10px;
        }}
        #dashNewsRow:hover {{
            border: 1px solid {P['BORDER_HOVER']};
            background: {P['CARD_HOVER']};
        }}
        #dashNewsRow[seen="true"] {{
            background: {P['PAUSED_BG']};
            border: 1px solid {P['PAUSED_BORDER']};
        }}
        #dashNewsRow[seen="true"] #dashNewsTitle {{
            color: {P['MUTED']};
        }}
        #dashNewsBullet {{
            color: {P['ACCENT']};
            font-size: 15px;
        }}
        #dashNewsTitle {{
            font-size: 13px;
            font-weight: 600;
            color: {P['TEXT']};
        }}

        QProgressBar {{
            background: {P['BTN']};
            border: 1px solid {P['BORDER']};
            border-radius: 8px;
            height: 14px;
            text-align: center;
            font-size: 11px;
            font-weight: 700;
            color: {P['TEXT']};
        }}
        QProgressBar::chunk {{
            background: {P['ACCENT']};
            border-radius: 7px;
        }}

        #taskCard {{
            background: {P['CARD']};
            border: 1px solid {P['BORDER']};
            border-radius: 12px;
        }}
        #taskCard:hover {{
            border: 1px solid {P['BORDER_HOVER']};
            background: {P['CARD_HOVER']};
        }}
        #taskCard[completed="true"] {{
            background: {P['PAUSED_BG']};
            border: 1px solid {P['PAUSED_BORDER']};
        }}
        #taskCard[overdue="true"] {{
            background: {P['DANGER_SOFT']};
            border: 1px solid {P['DANGER']};
        }}
        #taskCard[completed="true"] #taskTitle {{
            color: {P['MUTED']};
            text-decoration: line-through;
        }}
        #taskCard[completed="true"] #taskMeta {{
            color: {P['MUTED']};
        }}
        #taskCheck {{
            spacing: 10px;
        }}
        #taskCheck::indicator {{
            width: 20px;
            height: 20px;
            border: 2px solid {P['BORDER']};
            border-radius: 6px;
            background: {P['INPUT']};
        }}
        #taskCheck::indicator:hover {{ border: 2px solid {P['BORDER_HOVER']}; }}
        #taskCheck::indicator:checked {{
            background: {P['ACCENT']};
            border-color: {P['ACCENT']};
        }}
        #taskTitle {{
            font-size: 14px;
            font-weight: 600;
            color: {P['TEXT']};
        }}
        #taskMeta {{
            font-size: 12px;
            color: {P['MUTED']};
        }}
        #prodCard {{
            background: {P['CARD']};
            border: 1px solid {P['BORDER']};
            border-radius: 12px;
        }}
        #prodCard:hover {{
            border: 1px solid {P['BORDER_HOVER']};
            background: {P['CARD_HOVER']};
        }}
        #webcamCard {{
            background: {P['CARD']};
            border: 1px solid {P['BORDER']};
            border-radius: 12px;
        }}
        #webcamCard:hover {{
            border: 1px solid {P['BORDER_HOVER']};
            background: {P['CARD_HOVER']};
        }}
        #webcamCard[state="live"] {{
            border: 1px solid {P['OK']};
        }}
        #webcamCard[state="offline"] {{
            border: 1px solid {P['BORDER']};
        }}
        #webcamIcon {{
            min-width: 20px;
        }}
        #webcamName {{
            font-size: 15px;
            font-weight: 700;
            color: {P['TEXT']};
        }}
        #webcamLoc {{
            font-size: 12px;
            color: {P['MUTED']};
        }}
        #webcamState {{
            font-size: 11px;
            font-weight: 800;
            border-radius: 6px;
            padding: 2px 8px;
        }}
        #webcamState[state="live"] {{ background: {P['OK_SOFT']}; color: {P['OK']}; }}
        #webcamState[state="offline"] {{ background: {P['DANGER_SOFT']}; color: {P['DANGER']}; }}
        #webcamState[state="loading"] {{ background: {P['ACCENT_SOFT']}; color: {P['ACCENT']}; }}
        #webcamVideoArea {{
            background: #000000;
            border-radius: 10px;
        }}
        #webcamPoster {{
            background: #000000;
            border-radius: 10px;
        }}
        #webcamVideo {{
            background: #000000;
        }}
        #prodCard[hit="true"] {{
            background: {P['OK_SOFT']};
            border: 1px solid {P['OK']};
        }}
        #prodIcon {{
            min-width: 22px;
        }}
        #prodTitle {{
            font-size: 14px;
            font-weight: 600;
            color: {P['TEXT']};
        }}
        #prodMeta {{
            font-size: 12px;
            color: {P['MUTED']};
        }}
        #prodHit {{
            font-size: 11px;
            font-weight: 700;
            background: {P['OK_SOFT']};
            color: {P['OK']};
            border-radius: 6px;
            padding: 2px 8px;
        }}
        #prodPrice {{
            font-size: 17px;
            font-weight: 800;
            color: {P['TEXT']};
        }}
        #prodPrice[hit="true"] {{ color: {P['OK']}; }}
        #prodPrice[missing="true"] {{
            color: {P['MUTED']};
            font-weight: 600;
            font-size: 15px;
        }}
        #prodChart {{
            background: {P['INPUT']};
            border-top: 1px solid {P['BORDER']};
            border-radius: 0 0 12px 12px;
            margin: 0 2px 2px 2px;
        }}
        #webSearchRow {{
            background: {P['CARD']};
            border: 1px solid {P['BORDER']};
            border-radius: 12px;
        }}
        #webSearchRow:hover {{
            border: 1px solid {P['BORDER_HOVER']};
            background: {P['CARD_HOVER']};
        }}
        #webSearchTitle {{
            font-size: 13px;
            font-weight: 600;
            color: {P['TEXT']};
        }}
        #addBtnDone {{
            background: {P['OK_SOFT']};
            color: {P['OK']};
            border: none;
            padding: 6px 12px;
            font-size: 12px;
            font-weight: 700;
        }}
        #addBtnDone:disabled {{ background: {P['OK_SOFT']}; color: {P['OK']}; }}
        #prioBadge {{
            font-size: 11px;
            font-weight: 700;
            border-radius: 6px;
            padding: 2px 8px;
        }}
        #prioBadge[level="alta"] {{ background: {P['DANGER_SOFT']}; color: {P['DANGER']}; }}
        #prioBadge[level="media"] {{ background: {P['WARN_SOFT']}; color: {P['WARN']}; }}
        #prioBadge[level="baixa"] {{ background: {P['OK_SOFT']}; color: {P['OK']}; }}
        #catBadge {{
            color: {P['MUTED']};
            font-size: 11px;
            font-weight: 600;
            background: {P['BTN']};
            border: 1px solid {P['BORDER']};
            border-radius: 6px;
            padding: 2px 8px;
        }}
        #dueBadge {{
            font-size: 11px;
            font-weight: 700;
            border-radius: 6px;
            padding: 2px 8px;
        }}
        #dueBadge[state="overdue"] {{ background: {P['DANGER_SOFT']}; color: {P['DANGER']}; }}
        #dueBadge[state="today"] {{ background: {P['ACCENT_SOFT']}; color: {P['ACCENT']}; }}
        #dueBadge[state="tomorrow"] {{ background: {P['OK_SOFT']}; color: {P['OK']}; }}
        #dueBadge[state="future"] {{ background: {P['BTN']}; color: {P['MUTED']}; }}
        #filterBtn {{
            background: transparent;
            color: {P['MUTED']};
            border: none;
            border-radius: 8px;
            padding: 5px 12px;
            font-size: 12px;
            font-weight: 600;
        }}
        #filterBtn:hover {{ background: {P['BTN_HOVER']}; color: {P['TEXT']}; }}
        #filterBtn:checked {{ background: {P['ACCENT_SOFT']}; color: {P['ACCENT']}; }}

        #noteCard {{
            background: {P['CARD']};
            border: 1px solid {P['BORDER']};
            border-radius: 10px;
        }}
        #noteCard:hover {{
            border: 1px solid {P['BORDER_HOVER']};
            background: {P['CARD_HOVER']};
        }}
        #noteCard[active="true"] {{
            border: 1px solid {P['ACCENT']};
            background: {P['ACCENT_SOFT']};
        }}
        #noteTitle {{
            font-size: 14px;
            font-weight: 600;
            color: {P['TEXT']};
        }}
        #noteSnippet {{
            font-size: 12px;
            color: {P['MUTED']};
        }}
        #noteMeta {{
            font-size: 12px;
            color: {P['MUTED']};
        }}
        #noteTitleEdit {{
            font-size: 18px;
            font-weight: 700;
            color: {P['TEXT']};
        }}
        #notePreview, #noteEditor {{
            background: {P['CARD']};
            border: 1px solid {P['BORDER']};
            border-radius: 12px;
            padding: 6px;
        }}
        #attachChip {{
            background: {P['BTN']};
            border: 1px solid {P['BORDER']};
            border-radius: 8px;
        }}
        #attachChip:hover {{ border: 1px solid {P['BORDER_HOVER']}; }}
        #attachThumb {{
            background: {P['THUMB_BG']};
            border-radius: 6px;
        }}
        #attachName {{
            font-size: 12px;
            color: {P['TEXT']};
            max-width: 180px;
        }}

        #agendaRow {{
            background: {P['CARD']};
            border: 1px solid {P['BORDER']};
            border-radius: 10px;
        }}
        #agendaRow:hover {{
            border: 1px solid {P['BORDER_HOVER']};
            background: {P['CARD_HOVER']};
        }}
        #agendaRow[completed="true"] {{
            background: {P['PAUSED_BG']};
            border: 1px solid {P['PAUSED_BORDER']};
        }}
        #agendaRow[completed="true"] #taskTitle {{ color: {P['MUTED']}; text-decoration: line-through; }}
        #holidayRow {{
            background: {P['WARN_SOFT']};
            border: 1px solid {P['WARN']};
            border-radius: 10px;
        }}
        #holidayIcon {{
            min-width: 18px;
        }}
        #holidayBadge {{
            font-size: 11px;
            font-weight: 700;
            color: {P['WARN']};
            background: {P['WARN_SOFT']};
            border: 1px solid {P['WARN']};
            border-radius: 6px;
            padding: 2px 8px;
        }}
        #holidayName {{
            font-size: 13px;
            font-weight: 600;
            color: {P['TEXT']};
        }}
        #dayHeader {{
            font-size: 13px;
            font-weight: 800;
            color: {P['ACCENT']};
            padding: 4px 0;
        }}
        #calCell {{
            background: {P['CARD']};
            border: 1px solid {P['BORDER']};
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            color: {P['TEXT']};
            padding: 2px;
        }}
        #calCell:hover {{
            border: 1px solid {P['BORDER_HOVER']};
            background: {P['CARD_HOVER']};
        }}
        #calCell[today="true"] {{
            border: 1px solid {P['ACCENT']};
            color: {P['ACCENT']};
        }}
        #calCell[holiday="true"] {{
            color: {P['WARN']};
        }}
        #calCell[selected="true"] {{
            background: {P['ACCENT']};
            border: 1px solid {P['ACCENT']};
            color: #ffffff;
        }}
        #calCell[empty="true"] {{
            background: transparent;
            border: none;
        }}
        #calTitle {{
            font-size: 14px;
            font-weight: 800;
            color: {P['TEXT']};
        }}
        #weekCol {{
            background: {P['CARD']};
            border: 1px solid {P['BORDER']};
            border-radius: 10px;
        }}
        #weekColHead {{
            font-size: 13px;
            font-weight: 700;
            color: {P['MUTED']};
        }}
        #weekColHead[today="true"] {{
            color: {P['ACCENT']};
        }}
        #navBtn {{
            background: {P['BTN']};
            color: {P['TEXT']};
            border: 1px solid {P['BORDER']};
            border-radius: 8px;
            padding: 4px 10px;
            font-size: 13px;
        }}
        #navBtn:hover {{ background: {P['BTN_HOVER']}; }}

        #weatherCard, #dayCard {{
            background: {P['CARD']};
            border: 1px solid {P['BORDER']};
            border-radius: 12px;
        }}
        #clockTime {{
            font-size: 52px;
            font-weight: 700;
            color: {P['TEXT']};
            letter-spacing: 2px;
        }}
        #clockDate {{
            font-size: 16px;
            color: {P['MUTED']};
        }}
        #weatherTemp {{
            font-size: 44px;
            font-weight: 700;
            color: {P['TEXT']};
        }}
        #weatherDesc {{
            font-size: 17px;
            font-weight: 600;
            color: {P['TEXT']};
        }}
        #weatherMeta {{
            font-size: 13px;
            color: {P['MUTED']};
        }}
        #dayCardDay {{
            font-size: 13px;
            font-weight: 700;
            color: {P['ACCENT']};
            text-transform: uppercase;
        }}
        #dayCardDate {{
            font-size: 11px;
            color: {P['MUTED']};
        }}
        #dayCardTemp {{
            font-size: 15px;
            font-weight: 700;
            color: {P['TEXT']};
        }}
        #dayCardPrecip {{
            font-size: 11px;
            color: {P['MUTED']};
        }}
        #hourCard {{
            background: {P['CARD']};
            border: 1px solid {P['BORDER']};
            border-radius: 12px;
        }}
        #hourCard:hover {{ border: 1px solid {P['BORDER_HOVER']}; }}
        #hourLabel {{
            font-size: 12px;
            font-weight: 700;
            color: {P['ACCENT']};
        }}
        #hourTemp {{
            font-size: 15px;
            font-weight: 700;
            color: {P['TEXT']};
        }}
        #metricChip {{
            background: {P['BTN']};
            border: 1px solid {P['BORDER']};
            border-radius: 10px;
        }}
        #metricValue {{
            font-size: 14px;
            font-weight: 700;
            color: {P['TEXT']};
        }}
        #metricLabel {{
            font-size: 11px;
            color: {P['MUTED']};
        }}
        #newsThumb {{
            background: {P['THUMB_BG']};
            border-radius: 10px;
        }}
        #newsCategory {{
            color: {P['ACCENT']};
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
        }}
        #newsDate {{
            color: {P['MUTED']};
            font-size: 12px;
        }}
        #newsSource {{
            color: {P['MUTED']};
            font-size: 11px;
            font-weight: 600;
            background: {P['BTN']};
            border: 1px solid {P['BORDER']};
            border-radius: 6px;
            padding: 1px 8px;
        }}
        #newsTitle {{
            font-size: 14px;
            font-weight: 600;
            color: {P['TEXT']};
        }}
        #newsTime {{
            color: {P['MUTED']};
            font-size: 12px;
        }}
        #newsCard[seen="true"], #featuredCard[seen="true"] {{
            background: {P['PAUSED_BG']};
            border: 1px solid {P['PAUSED_BORDER']};
        }}
        #newsCard[seen="true"] #newsTitle, #featuredCard[seen="true"] #featuredTitle {{
            color: {P['MUTED']};
        }}
        #cardBtn {{
            background: transparent;
            border: none;
            border-radius: 8px;
        }}
        #cardBtn:hover {{ background: {P['BTN_HOVER']}; }}
        #savedBadge {{
            background: {P['ACCENT_SOFT']};
            border-radius: 4px;
            padding: 2px 4px;
        }}

        #featuredCard {{
            background: {P['CARD']};
            border: 1px solid {P['BORDER']};
            border-radius: 16px;
        }}
        #featuredCard:hover {{
            border: 1px solid {P['BORDER_HOVER']};
            background: {P['CARD_HOVER']};
        }}
        #featuredTitle {{
            font-size: 19px;
            font-weight: 700;
            color: {P['TEXT']};
        }}
        #featuredThumb {{
            background: {P['THUMB_BG']};
            border-radius: 12px;
        }}

        #tabBtn {{
            background: transparent;
            color: {P['MUTED']};
            border: none;
            border-radius: 8px;
            padding: 6px 14px;
            font-size: 13px;
            font-weight: 600;
        }}
        #tabBtn:hover {{ background: {P['BTN_HOVER']}; color: {P['TEXT']}; }}
        #tabBtn:checked {{ background: {P['ACCENT_SOFT']}; color: {P['ACCENT']}; }}

        #sourceBtn {{
            background: {P['BTN']};
            color: {P['MUTED']};
            border: 1px solid {P['BORDER']};
            border-radius: 999px;
            padding: 4px 12px;
            font-size: 12px;
            font-weight: 600;
        }}
        #sourceBtn:hover {{ color: {P['TEXT']}; border-color: {P['BORDER_HOVER']}; }}
        #sourceBtn:checked {{ background: {P['ACCENT']}; color: #ffffff; border-color: {P['ACCENT']}; }}

        #newsSearch {{
            background: {P['INPUT']};
            border: 1px solid {P['BORDER']};
            border-radius: 999px;
            padding: 6px 14px;
            font-size: 13px;
        }}
        #newsSearch:focus {{ border: 1px solid {P['ACCENT']}; }}

        #searchRow {{
            background: {P['CARD']};
            border: 1px solid {P['BORDER']};
            border-radius: 10px;
        }}
        #searchRow:hover {{
            border: 1px solid {P['BORDER_HOVER']};
            background: {P['CARD_HOVER']};
        }}
        #searchRow[selected="true"] {{
            background: {P['ACCENT_SOFT']};
            border: 1px solid {P['ACCENT']};
        }}
        #searchRow[selected="true"] #searchTitle {{ color: {P['ACCENT']}; }}
        #searchIcon {{
            min-width: 20px;
        }}
        #searchTitle {{
            font-size: 13px;
            font-weight: 600;
            color: {P['TEXT']};
        }}
        #searchSnippet {{
            font-size: 12px;
            color: {P['MUTED']};
        }}
        #searchTag {{
            color: {P['MUTED']};
            font-size: 11px;
            font-weight: 600;
            background: {P['BTN']};
            border: 1px solid {P['BORDER']};
            border-radius: 6px;
            padding: 2px 8px;
        }}
        #searchSection {{
            font-size: 12px;
            font-weight: 800;
            color: {P['ACCENT']};
            padding: 8px 2px 2px;
        }}
        #searchEmpty {{
            color: {P['MUTED']};
            font-size: 13px;
            padding: 30px;
        }}

        #emptyLabel {{
            color: {P['MUTED']};
            font-size: 14px;
            padding: 40px;
        }}
        #undoBar {{
            background: {P['ACCENT_SOFT']};
            border: 1px solid {P['BORDER']};
            border-radius: 10px;
            padding: 6px 10px;
        }}
        #undoBar QLabel {{ color: {P['TEXT']}; font-size: 13px; }}
        #errorLabel {{
            color: {P['DANGER']};
            font-size: 14px;
            padding: 30px;
            background: {P['CARD']};
            border: 1px solid {P['DANGER_SOFT']};
            border-radius: 12px;
        }}
        #reminderIcon {{
            min-width: 22px;
        }}
        #reminderTitle {{
            font-size: 14px;
            font-weight: 700;
            color: {P['TEXT']};
        }}
        #reminderMeta {{
            font-size: 12px;
            color: {P['MUTED']};
        }}

        QLineEdit, QTimeEdit, QDateEdit, QSpinBox, QComboBox {{
            padding: 8px 10px;
            border: 1px solid {P['BORDER']};
            border-radius: 8px;
            background: {P['INPUT']};
            color: {P['TEXT']};
            font-size: 13px;
            selection-background-color: {P['ACCENT']};
        }}
        QLineEdit:focus, QTimeEdit:focus, QDateEdit:focus, QSpinBox:focus, QComboBox:focus {{
            border: 1px solid {P['ACCENT']};
        }}
        QLineEdit::placeholder {{ color: {P['PLACEHOLDER']}; }}
        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}
        QComboBox QAbstractItemView {{
            background: {P['SURFACE']};
            color: {P['TEXT']};
            border: 1px solid {P['BORDER']};
            border-radius: 8px;
            selection-background-color: {P['SIDEBAR_SELECTED']};
            padding: 4px;
        }}
        QCheckBox {{
            color: {P['TEXT']};
            font-size: 13px;
            spacing: 8px;
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {P['BORDER']};
            border-radius: 4px;
            background: {P['INPUT']};
        }}
        QCheckBox::indicator:checked {{
            background: {P['ACCENT']};
            border-color: {P['ACCENT']};
        }}
        QTimeEdit::up-button, QTimeEdit::down-button,
        QSpinBox::up-button, QSpinBox::down-button,
        QDateEdit::up-button, QDateEdit::down-button {{
            background: transparent;
            border: none;
            width: 16px;
        }}
        QDateEdit::drop-down {{
            border: none;
            width: 26px;
            background: transparent;
        }}
        QCalendarWidget QWidget {{
            background: {P['SURFACE']};
            color: {P['TEXT']};
        }}
        QCalendarWidget QAbstractItemView {{
            background: {P['SURFACE']};
            color: {P['TEXT']};
            selection-background-color: {P['ACCENT']};
            selection-color: #ffffff;
        }}
        QCalendarWidget QToolButton {{
            background: transparent;
            border: none;
            border-radius: 6px;
            color: {P['TEXT']};
            padding: 4px 8px;
        }}
        QDialogButtonBox QPushButton {{
            min-width: 84px;
        }}
        QMessageBox QLabel {{
            color: {P['TEXT']};
        }}
    
    """
    return _scale_font_sizes(sheet, font_scale)
