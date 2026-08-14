"""Testes para news.py (dados e regras de notícias, sem UI)."""

import datetime
import json

import pytest

import news


@pytest.mark.parametrize("text, expected", [
    ("agora", 0),
    ("hoje", 0),
    ("ontem", -1),
    ("anteontem", -2),
    ("há 30 minutos", 30),
    ("há 2 horas", 2),
    ("há 3 dias", 3),
])
def test_parse_news_datetime_relative(text, expected):
    now = datetime.datetime(2026, 8, 12, 12, 0, 0)
    result = news.parse_news_datetime(text, now)
    if text == "agora":
        expected_dt = now
    elif text == "hoje":
        expected_dt = now
    elif text == "ontem":
        expected_dt = now - datetime.timedelta(days=1)
    elif text == "anteontem":
        expected_dt = now - datetime.timedelta(days=2)
    elif "minuto" in text:
        expected_dt = now - datetime.timedelta(minutes=expected)
    elif "hora" in text:
        expected_dt = now - datetime.timedelta(hours=expected)
    else:
        expected_dt = now - datetime.timedelta(days=expected)
    assert result == expected_dt


def test_parse_news_datetime_br_iso():
    assert news.parse_news_datetime("12/08/2026") == datetime.datetime(2026, 8, 12)
    assert news.parse_news_datetime("12/08/2026 10:30") == datetime.datetime(2026, 8, 12, 10, 30)
    assert news.parse_news_datetime("12 de agosto de 2026") == datetime.datetime(2026, 8, 12)
    assert news.parse_news_datetime("12 de agosto de 2026 às 08:05") == datetime.datetime(2026, 8, 12, 8, 5)


def test_parse_news_datetime_invalid():
    assert news.parse_news_datetime(None) is None
    assert news.parse_news_datetime("") is None
    assert news.parse_news_datetime("não é uma data") is None
    assert news.parse_news_datetime("32/13/2026") is None


def test_sort_by_date_recent_first():
    items = [
        {"title": "velha", "date": "01/08/2026"},
        {"title": "nova", "date": "10/08/2026"},
        {"title": "sem data", "date": ""},
    ]
    result = news.sort_by_date(items)
    titles = [item["title"] for item in result]
    assert titles == ["nova", "velha", "sem data"]


def test_sort_by_date_limit():
    items = [
        {"title": "a", "date": "10/08/2026"},
        {"title": "b", "date": "09/08/2026"},
        {"title": "c", "date": "08/08/2026"},
    ]
    assert [i["title"] for i in news.sort_by_date(items, limit=2)] == ["a", "b"]


def test_relative_time_future_returns_empty():
    later = (datetime.date.today() + datetime.timedelta(days=10)).strftime("%d/%m/%Y")
    assert news._relative_time(later) == ""


def test_relative_time_empty():
    assert news._relative_time("") == ""
    assert news._relative_time(None) == ""


def test_state_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(news, "STATE_FILE", tmp_path / "estado.json")
    state = {"saved": ["a"], "hidden": [], "seen": ["x", "y"]}
    news._save_state(state)
    loaded = news._load_state()
    assert loaded == state


def test_state_load_missing(monkeypatch):
    monkeypatch.setattr(news, "STATE_FILE", __import__("pathlib").Path("C:/sem_arquivo_inexistente.json"))
    assert news._load_state() == {"saved": [], "hidden": [], "seen": []}


def test_as_snapshot_defaults():
    assert news._as_snapshot({}) == {
        "title": "", "url": "", "image": "", "category": "", "date": "", "source": "",
    }