"""Testes para tasks.py (gerenciamento de tarefas, sem UI)."""

import datetime
import uuid

import pytest

import tasks
from tasks import Task, TaskManager, next_occurrence


def _today():
    return datetime.date.today()


def test_next_occurrence_no_input():
    assert next_occurrence("", "") == ""
    assert next_occurrence("2026-08-01", "") == ""
    assert next_occurrence("", "diaria") == ""
    assert next_occurrence("data-invalida", "diaria") == ""


def test_next_occurrence_daily():
    assert next_occurrence("2099-01-01", "diaria") == "2099-01-02"


def test_next_occurrence_weekly():
    assert next_occurrence("2099-01-01", "semanal") == "2099-01-08"


def test_next_occurrence_monthly_not_december():
    assert next_occurrence("2099-02-10", "mensal") == "2099-03-10"


def test_next_occurrence_monthly_december():
    assert next_occurrence("2099-12-15", "mensal") == "2100-01-15"


def test_next_occurrence_monthly_clamps_day():
    # 31 de janeiro + 1 mês → 28/02 (ano não-bissexto)
    assert next_occurrence("2098-01-31", "mensal") == "2098-02-28"


def test_taskmanager_roundtrip(tmp_path):
    path = tmp_path / "tarefas.txt"
    mgr = TaskManager(path)
    task = mgr.add("Comprar leite", description="1L", due="2099-12-31", priority="alta",
                   category="Casa", recurrence="semanal")
    assert len(mgr.tasks) == 1

    mgr2 = TaskManager(path)
    assert len(mgr2.tasks) == 1
    loaded = mgr2.tasks[0]
    assert loaded.title == "Comprar leite"
    assert loaded.description == "1L"
    assert loaded.due == "2099-12-31"
    assert loaded.priority == "alta"
    assert loaded.category == "Casa"
    assert loaded.recurrence == "semanal"


def test_taskmanager_add_completed_sets_date(tmp_path):
    mgr = TaskManager(tmp_path / "t.txt")
    t = mgr.add("feita", completed=True)
    assert t.completed is True
    assert t.completed_at == _today().isoformat()


def test_taskmanager_load_missing_file(tmp_path):
    mgr = TaskManager(tmp_path / "nao_existe.txt")
    assert mgr.tasks == []


def test_taskmanager_remove(tmp_path):
    mgr = TaskManager(tmp_path / "t.txt")
    a = mgr.add("a")
    b = mgr.add("b")
    mgr.remove(a.id)
    assert [t.id for t in mgr.tasks] == [b.id]


def test_taskmanager_toggle_recurring_creates_next(tmp_path):
    mgr = TaskManager(tmp_path / "t.txt")
    t = mgr.add("diária", recurrence="diaria", due="2099-01-01")
    mgr.toggle(t.id)
    completed = [x for x in mgr.tasks if x.completed]
    open_tasks = [x for x in mgr.tasks if not x.completed]
    assert len(completed) == 1 and completed[0].id == t.id
    assert len(open_tasks) == 1
    assert open_tasks[0].due == "2099-01-02"
    assert open_tasks[0].recurrence == "diaria"


def test_taskmanager_overdue_and_mark(tmp_path):
    mgr = TaskManager(tmp_path / "t.txt")
    mgr.add("atrasada", due="2000-01-01")
    mgr.add("futura", due="2099-01-01")
    mgr.add("concluida", due="2000-01-01", completed=True)
    today = _today()
    overdue = mgr.overdue_tasks(today=today)
    assert [t.title for t in overdue] == ["atrasada"]

    ids = [t.id for t in overdue]
    mgr.mark_overdue_notified(ids, day=today.isoformat())
    assert mgr.tasks[0].overdue_notified == today.isoformat()


def test_taskmanager_search(tmp_path):
    mgr = TaskManager(tmp_path / "t.txt")
    mgr.add("Pagar energia", category="Contas")
    mgr.add("Estudar python", category="Estudo")
    assert len(mgr.search("energia")) == 1
    assert mgr.search("contas")[0].title == "Pagar energia"
    assert len(mgr.search("inexistente")) == 0
    assert len(mgr.search("")) == 2


def test_taskmanager_category_stats(tmp_path):
    mgr = TaskManager(tmp_path / "t.txt")
    mgr.add("a", category="Casa")
    mgr.add("b", category="Casa", completed=True)
    mgr.add("c", category="Trabalho")
    stats = mgr.category_stats()
    by_cat = {s["category"]: s for s in stats}
    assert by_cat["Casa"] == {"category": "Casa", "total": 2, "done": 1, "pct": 50}
    assert by_cat["Trabalho"]["pct"] == 0


def test_taskmanager_parse_legacy_line():
    task = TaskManager._parse_legacy("id1|Título|desc|2099-01-01|1")
    assert task.id == "id1"
    assert task.title == "Título"
    assert task.completed is True
    assert TaskManager._parse_legacy("apenas|dois") is None


def test_taskmanager_streak_and_completed_last_days(tmp_path):
    mgr = TaskManager(tmp_path / "t.txt")
    today = _today()
    for i in range(3):
        t = Task(id=uuid.uuid4().hex, title=str(i), completed=True,
                 completed_at=(today - datetime.timedelta(days=i)).isoformat())
        mgr.tasks.append(t)
    mgr.save()
    assert mgr.streak_days() == 3
    last7 = mgr.completed_last_days(days=7)
    assert len(last7) == 7
    assert sum(count for _, count in last7) == 3