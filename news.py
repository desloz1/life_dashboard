"""Dados e regras de notícias (sem UI).

Responsável por: estado persistido (salvas/ocultas/vistas), snapshot de itens,
data relativa e ordenação por data. A interface está em ``news_ui.py``.
"""

import datetime
import json
import re
from pathlib import Path

import log

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