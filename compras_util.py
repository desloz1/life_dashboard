"""Utilitários de formatação da aba Compras (preço e data)."""

import datetime


def format_price(value):
    if value is None:
        return "—"
    return "R$ {:,.2f}".format(value).replace(",", "X").replace(".", ",").replace("X", ".")


def format_datetime(iso):
    if not iso:
        return ""
    try:
        dt = datetime.datetime.fromisoformat(iso)
    except (ValueError, TypeError):
        return ""
    return dt.strftime("%d/%m %H:%M")