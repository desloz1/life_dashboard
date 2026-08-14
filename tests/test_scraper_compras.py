"""Testes para scraper_compras_core.py (preço/URL/challenge, sem rede)."""

import pytest

import scraper_compras_core as core
from scraper_compras_core import normalize_price, store_name


@pytest.mark.parametrize("value, expected", [
    (None, None),
    ("", None),
    ("R$ 1.234,56", 1234.56),
    ("1.234,56", 1234.56),
    ("R$ 99,90", 99.9),
    ("1234.56", 1234.56),       # ponto separando centavos (1234.56)
    ("R$ 0,", 0.0),
    ("1.000", 1000.0),          # agrupador de milhar sem decimais
    ("123", 123.0),
    (1234.5678, 1234.57),       # número → arredondado
    (99, 99.0),
])
def test_normalize_price(value, expected):
    assert normalize_price(value) == expected


@pytest.mark.parametrize("value", ["abc", "1,234,56", "..", "12,34,56"])
def test_normalize_price_invalid(value):
    # casos sem um formato válido podem retornar algo ou None; não devem crashar
    result = normalize_price(value)
    assert result is None or isinstance(result, float)


def test_normalize_price_original_behavior_preserved():
    # Comportamento legado documentado: dois preços aninhados viram um só número.
    assert normalize_price("R$ 1.234,56 2.345,67") == 1234562345.67


def test_normalize_price_int_string_no_decimal():
    assert normalize_price("1000") == 1000.0


@pytest.mark.parametrize("url, expected", [
    ("https://www.amazon.com.br/produto/123", "Amazon"),
    ("https://amazon.com/item", "Amazon"),
    ("https://www.mercadolivre.com.br/abc", "Mercado Livre"),
    ("https://www.magazineluiza.com.br/produto", "Magazine Luiza"),
    ("https://www.kabum.com.br/produto", "Kabum"),
    ("https://meuloja.com.br/item", "meuloja.com.br"),  # domínio desconhecido
    ("https://www.google.com/x", "google.com"),
    ("", "Loja"),
    (None, "Loja"),
])
def test_store_name(url, expected):
    assert store_name(url) == expected


def test_blocked_error_is_exception():
    assert issubclass(core.BlockedError, Exception)


def test_constants():
    assert "Amazon" in core.STORES
    assert "mercadolivre.com.br" in core.STORES["Mercado Livre"]["domains"]
    assert "Magazine Luiza" in core.UNSUPPORTED_STORES
    assert core.MIN_HTML_LEN > 0


def test_unsupported_in_stores():
    assert "Magazine Luiza" in core.STORES