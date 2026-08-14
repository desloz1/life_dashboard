"""Core do engine de compras: config, utilitários de preço/URL e detecção de desafio.

Sem lógica de parse por loja nem de navegador — só o que os demais módulos
reutilizam (constantes, exceções, limpeza de texto, detecção de loja e
conversão de preço).
"""

import re
from urllib.parse import urlparse

from scrapling.parser import Selector

STORES = {
    "Amazon": {"domains": ("amazon.com.br", "amazon.com"), "price": "_amazon_price"},
    "Mercado Livre": {
        "domains": ("mercadolivre.com.br", "mercadolivre.com", "mercadolibre.com.br"),
        "price": "_ml_price",
    },
    "Magazine Luiza": {"domains": ("magazineluiza.com.br",)},
    "Casas Bahia": {"domains": ("casasbahia.com.br",)},
    "Americanas": {"domains": ("americanas.com.br",)},
    "Kabum": {"domains": ("kabum.com.br",)},
    "Pichau": {"domains": ("pichau.com.br",)},
    "Terabyte": {"domains": ("terabyteshop.com.br",)},
}

UNSUPPORTED_STORES = {"Magazine Luiza"}

MIN_HTML_LEN = 5000

# Marcadores de desafio/anti-bot que disparam a escalada para navegador/stealth.
_CHALLENGE_MARKERS = (
    "cf-challenge",
    "cf_chl",
    "__cf_chl",
    "jschl",
    "just a moment",
    "unusual traffic",
    "please verify you are a human",
    "captcha",
    "challenge-platform",
    "robot check",
    "um momento",
    "verify you are human",
    "antibot",
    "anti-bot",
    "access denied",
    "attention required",
)


class BlockedError(Exception):
    """A loja bloqueou a coleta (anti-bot/desafio); o chamador deve escalar de camada."""


def _clean(text):
    return (text or "").replace("\ufeff", "").strip()


def _domain(url):
    try:
        return (urlparse(url).netloc or "").lower()
    except ValueError:
        return ""


def _store_entry(url):
    host = _domain(url)
    for name, entry in STORES.items():
        for dom in entry["domains"]:
            if host == dom or host.endswith("." + dom):
                return name, entry
    return "", None


def store_name(url):
    name, _entry = _store_entry(url)
    if name:
        return name
    return _domain(url).replace("www.", "") or "Loja"


def normalize_price(value):
    """Converte texto de preço brasileiro ('R$ 1.234,56') em float (1234.56)."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return round(float(value), 2)
        except (TypeError, ValueError):
            return None
    text = str(value).strip()
    if not text:
        return None
    text = re.sub(r"[^\d.,]", "", text)
    if not text:
        return None
    has_comma = "," in text
    has_dot = "." in text

    if has_comma and has_dot:
        last_comma = text.rfind(",")
        last_dot = text.rfind(".")
        if last_comma > last_dot:
            integer = text[:last_comma].replace(".", "").replace(",", "")
            decimal = text[last_comma + 1:]
        else:
            integer = text[:last_dot].replace(",", "").replace(".", "")
            decimal = text[last_dot + 1:]
        return _to_float(integer, decimal)

    if has_comma:
        parts = text.split(",")
        if len(parts) > 2:
            return None
        return _to_float(parts[0].replace(".", ""), parts[1] if len(parts) > 1 else "")

    if has_dot:
        parts = text.split(".")
        if len(parts) == 2 and len(parts[1]) == 3:
            return _to_float(parts[0] + parts[1], "")
        if len(parts) > 2:
            return None
        return _to_float(parts[0], parts[1] if len(parts) > 1 else "")

    return _to_float(text, "")


def _to_float(integer, decimal):
    integer = (integer or "0").strip() or "0"
    decimal = (decimal or "").strip() or "0"
    try:
        return round(float(integer + "." + decimal), 2)
    except ValueError:
        return None


def _is_challenge(page):
    """Detecta padrões típicos de desafio/anti-bot numa página carregada."""
    try:
        haystack = _clean(str(page.get_all_text())).lower()
    except Exception:
        haystack = ""
    return any(marker in haystack for marker in _CHALLENGE_MARKERS)


def _build_selector(content, url):
    """Constrói um Selector (com adaptive habilitado) a partir do HTML bruto."""
    return Selector(content, url=url, adaptive=True)