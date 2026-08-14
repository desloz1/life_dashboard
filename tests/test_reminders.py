"""Testes para reminders.py (gerenciamento de lembretes, sem UI)."""

import datetime

import pytest

import reminders
from reminders import (
    Reminder,
    ReminderManager,
    compute_next_trigger,
    current_occurrence,
    describe_schedule,
    format_next,
    is_done,
    is_overdue,
    is_snoozed,
    parse_reminder,
    serialize_reminder,
)


def _rem(**kw):
    base = dict(id="r1", title="teste", trigger_type="one_time", time="09:00")
    base.update(kw)
    return Reminder(**base)


NOW = datetime.datetime(2026, 8, 12, 10, 0, 0)


def test_compute_next_one_time():
    r = _rem(date="2026-08-13")
    assert compute_next_trigger(r, NOW) == datetime.datetime(2026, 8, 13, 9, 0, 0)


def test_compute_next_one_time_past():
    r = _rem(date="2026-08-01")
    assert compute_next_trigger(r, NOW) is None
    r2 = _rem(trigger_type="one_time", date="")
    assert compute_next_trigger(r2, NOW) is None


def test_compute_next_daily():
    r = _rem(trigger_type="daily", time="11:00")
    assert compute_next_trigger(r, NOW) == datetime.datetime(2026, 8, 12, 11, 0, 0)
    r2 = _rem(trigger_type="daily", time="09:00")
    assert compute_next_trigger(r2, NOW) == datetime.datetime(2026, 8, 13, 9, 0, 0)


def test_compute_next_weekly():
    # 2026-08-12 é quarta-feira (weekday=2). Sábado presente (weekday=5).
    r = _rem(trigger_type="weekly", weekdays=[5], time="09:00")
    assert compute_next_trigger(r, NOW) == datetime.datetime(2026, 8, 15, 9, 0, 0)
    r2 = _rem(trigger_type="weekly", weekdays=[], time="09:00")
    assert compute_next_trigger(r2, NOW) is None


def test_compute_next_monthly():
    # monthly sempre calcula a partir do próximo mês
    r = _rem(trigger_type="monthly", day_of_month=20, time="09:00")
    assert compute_next_trigger(r, NOW) == datetime.datetime(2026, 9, 20, 9, 0, 0)


def test_current_occurrence_daily():
    r = _rem(trigger_type="daily", time="08:00")
    assert current_occurrence(r, NOW) == datetime.datetime(2026, 8, 12, 8, 0, 0)


def test_current_occurrence_one_time():
    r = _rem(date="2026-08-20")
    assert current_occurrence(r, NOW) == datetime.datetime(2026, 8, 20, 9, 0, 0)
    assert current_occurrence(_rem(trigger_type="one_time", date=""), NOW) is None


def test_is_snoozed():
    future = (NOW + datetime.timedelta(minutes=30)).isoformat()
    assert is_snoozed(_rem(snooze_until=future), NOW) is True
    past = (NOW - datetime.timedelta(minutes=30)).isoformat()
    assert is_snoozed(_rem(snooze_until=past), NOW) is False
    assert is_snoozed(_rem(snooze_until=""), NOW) is False


def test_is_overdue():
    past = _rem(next_trigger="2026-08-12T09:00:00", enabled=True)
    assert is_overdue(past, NOW) is True
    future = _rem(next_trigger="2026-08-12T11:00:00", enabled=True)
    assert is_overdue(future, NOW) is False
    disabled = _rem(next_trigger="2026-08-12T09:00:00", enabled=False)
    assert is_overdue(disabled, NOW) is False


def test_is_done():
    daily = _rem(trigger_type="daily", time="08:00", done_for="2026-08-12T08:00:00")
    assert is_done(daily, NOW) is True
    daily.done_for = "2026-08-11T08:00:00"
    assert is_done(daily, NOW) is False


def test_describe_schedule():
    assert "Diária" in describe_schedule(_rem(trigger_type="daily", time="09:00"))
    assert describe_schedule(_rem(trigger_type="one_time", date="")) == "Única às 09:00 (sem data)"
    assert "Semanal" in describe_schedule(_rem(trigger_type="weekly", weekdays=[0, 1]))
    assert "Mensal dia 10" in describe_schedule(_rem(trigger_type="monthly", day_of_month=10))


def test_format_next():
    assert format_next("") == "Sem alarme agendado"
    today = datetime.datetime(2026, 8, 12, 9, 0, 0)
    assert format_next("2026-08-12T09:00:00", NOW) == "Hoje às 09:00"
    assert format_next("2026-08-13T09:00:00", NOW) == "Amanhã às 09:00"
    assert format_next("2026-09-01T09:00:00", NOW) == "01/09/2026 às 09:00"


def test_serde_roundtrip():
    r = Reminder(
        id="abc123", title="Reunião", description="com time",
        trigger_type="weekly", time="14:30", weekdays=[0, 3], day_of_month=1,
        enabled=True, done_for="2026-08-10T14:30:00",
    )
    text = serialize_reminder(r)
    parsed = parse_reminder(text.splitlines())
    assert parsed.title == "Reunião"
    assert parsed.trigger_type == "weekly"
    assert parsed.time == "14:30"
    assert sorted(parsed.weekdays) == [0, 3]
    assert parsed.enabled is True
    assert parsed.done_for == "2026-08-10T14:30:00"


def test_parse_reminder_pt_weekdays():
    lines = [
        "ID: x1", "Título: Academia", "Recorrência: semanal", "Horário: 07:00",
        "Dias: Seg, Qua, Sex", "Ativo: sim", "Finalizado: ",
    ]
    r = parse_reminder(lines)
    assert sorted(r.weekdays) == [0, 2, 4]


def test_parse_reminder_requires_title():
    assert parse_reminder(["ID: a", "Título: "]) is None


def test_remindermanager_roundtrip(tmp_path):
    path = tmp_path / "lembretes.txt"
    mgr = ReminderManager(path)
    r = mgr.add("Beber água", trigger_type="daily", time="12:00")
    assert len(mgr.reminders) == 1

    mgr2 = ReminderManager(path)
    assert len(mgr2.reminders) == 1
    assert mgr2.reminders[0].title == "Beber água"
    assert mgr2.reminders[0].trigger_type == "daily"
    assert len(mgr2.reminders[0].next_trigger) > 0


def test_remindermanager_remove_toggle(tmp_path):
    mgr = ReminderManager(tmp_path / "l.txt")
    r = mgr.add("um")
    mgr.add("dois")
    mgr.remove(r.id)
    assert [x.title for x in mgr.reminders] == ["dois"]
    mgr.toggle(mgr.reminders[0].id)
    assert mgr.reminders[0].enabled is False
    assert mgr.reminders[0].next_trigger == ""


def test_remindermanager_snooze(tmp_path):
    mgr = ReminderManager(tmp_path / "l.txt")
    r = mgr.add("x", trigger_type="daily", time="09:00")
    assert mgr.snooze(r.id, 15) is True
    assert mgr.reminders[0].enabled is True
    assert len(mgr.reminders[0].snooze_until) > 0


def test_remindermanager_mark_done_one_time_disables(tmp_path):
    mgr = ReminderManager(tmp_path / "l.txt")
    r = mgr.add("agora", trigger_type="one_time", date="2026-08-12")
    mgr.mark_done(r.id, True, now=NOW)
    assert mgr.reminders[0].enabled is False
    assert mgr.reminders[0].done_for != ""


def test_remindermanager_search_and_check_due(tmp_path):
    mgr = ReminderManager(tmp_path / "l.txt")
    r = mgr.add("pagar conta", trigger_type="daily", time="00:00")
    assert len(mgr.search("conta")) == 1
    # força um gatilho já vencido para disparar check_due
    r.next_trigger = "2026-08-08T09:00:00"
    fired = mgr.check_due(now=NOW)
    assert fired == [mgr.reminders[0]]