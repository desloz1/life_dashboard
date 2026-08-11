import datetime

FIXED = [
    (1, 1, "Confraternização Universal"),
    (4, 21, "Tiradentes"),
    (5, 1, "Dia do Trabalho"),
    (9, 7, "Independência do Brasil"),
    (10, 12, "Nossa Senhora Aparecida"),
    (11, 2, "Finados"),
    (11, 15, "Proclamação da República"),
    (11, 20, "Consciência Negra"),
    (12, 25, "Natal"),
]


def _easter(year):
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return datetime.date(year, month, day)


def national_holidays(year):
    easter = _easter(year)
    by_date = {
        easter - datetime.timedelta(days=48): "Carnaval",
        easter - datetime.timedelta(days=47): "Carnaval",
        easter - datetime.timedelta(days=2): "Sexta-feira Santa",
        easter: "Páscoa",
        easter + datetime.timedelta(days=60): "Corpus Christi",
    }
    for month, day, name in FIXED:
        by_date[datetime.date(year, month, day)] = name
    return sorted(by_date.items())


def holidays_for(date):
    return [name for d, name in national_holidays(date.year) if d == date]
