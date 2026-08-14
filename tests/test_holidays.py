"""Testes para holidays.py (feriados nacionais, cálculo puro)."""

import datetime

import pytest

import holidays
from holidays import holidays_for, national_holidays


def test_fixed_holidays_present():
    dates = dict(national_holidays(2026))
    assert dates[datetime.date(2026, 1, 1)] == "Confraternização Universal"
    assert dates[datetime.date(2026, 12, 25)] == "Natal"
    assert dates[datetime.date(2026, 11, 20)] == "Consciência Negra"


def test_movable_holidays_2026():
    # Páscoa 2026 = 5 de abril (domingo)
    dates = dict(national_holidays(2026))
    assert dates[datetime.date(2026, 4, 5)] == "Páscoa"
    assert dates[datetime.date(2026, 4, 3)] == "Sexta-feira Santa"
    assert dates[datetime.date(2026, 2, 16)] == "Carnaval"   # segunda
    assert dates[datetime.date(2026, 2, 17)] == "Carnaval"   # terça
    # Corpus Christi = 60 dias depois da Páscoa
    assert dates[datetime.date(2026, 6, 4)] == "Corpus Christi"


def test_national_holidays_sorted():
    dates = national_holidays(2026)
    keys = [d for d, _ in dates]
    assert keys == sorted(keys)


def test_holidays_for():
    assert holidays_for(datetime.date(2026, 12, 25)) == ["Natal"]
    assert holidays_for(datetime.date(2026, 4, 5)) == ["Páscoa"]
    assert holidays_for(datetime.date(2026, 8, 12)) == []