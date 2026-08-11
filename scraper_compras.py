import json
import re
from urllib.parse import urlparse

import requests
from lxml import html

try:
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
    pass

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
}

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

OG_PRICE_PROPS = ("og:price:amount", "product:price:amount", "og:price:amount:usd")

UNSUPPORTED_STORES = {"Magazine Luiza"}

MIN_HTML_LEN = 5000


class BlockedError(Exception):
    """Requests foi bloqueado pela loja (anti-bot); usar navegador."""


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


def _extract_product(node, out):
    if isinstance(node, list):
        for item in node:
            _extract_product(item, out)
        return
    if not isinstance(node, dict):
        return
    if "@graph" in node:
        _extract_product(node["@graph"], out)
    ntype = node.get("@type")
    types = ntype if isinstance(ntype, list) else ([ntype] if ntype else [])
    is_product = any("Product" in str(t) for t in types)
    is_offer = any("Offer" in str(t) for t in types)
    if is_product:
        name = node.get("name") or node.get("alternateName")
        if name and not out.get("name"):
            out["name"] = _clean(name)
        offers = node.get("offers")
        if offers is not None:
            _extract_product(offers, out)
    if is_offer:
        for key in ("price", "lowPrice", "highPrice"):
            value = node.get(key)
            if value not in (None, ""):
                price = normalize_price(value)
                if price is not None and out.get("price") is None:
                    out["price"] = price
                break
    for value in node.values():
        if isinstance(value, (dict, list)):
            _extract_product(value, out)


def _json_ld(tree):
    for script in tree.xpath('//script[@type="application/ld+json"]'):
        text = (script.text or "").strip()
        if not text:
            continue
        try:
            data = json.loads(text)
        except ValueError:
            continue
        out = {}
        _extract_product(data, out)
        if out.get("name") or out.get("price") is not None:
            return out
    return None


def _og_meta(tree):
    props = {}
    for meta in tree.xpath("//meta"):
        prop = (meta.get("property") or meta.get("name") or "").strip()
        if not prop or prop in props:
            continue
        value = (meta.get("content") or "").strip()
        if value:
            props[prop.lower()] = value
    return props


def _page_title(tree):
    nodes = tree.xpath("//title")
    return _clean(nodes[0].text_content()) if nodes else ""


def _amazon_price(tree):
    node = tree.xpath('//span[contains(@class, "a-offscreen")]')
    if not node:
        return None
    return normalize_price(_clean(node[0].text_content()))


def _ml_price(tree):
    frac = tree.xpath('//span[contains(@class, "andes-money-amount__fraction")]')
    if not frac:
        return None
    text = _clean(frac[0].text_content())
    cents = tree.xpath('//span[contains(@class, "andes-money-amount__cents")]')
    if cents:
        text += "," + _clean(cents[0].text_content())
    return normalize_price(text)


def _store_price(tree, url):
    name, entry = _store_entry(url)
    if not entry or not entry.get("price"):
        return None
    fn = globals().get(entry["price"])
    if fn is None:
        return None
    try:
        return fn(tree)
    except Exception:
        return None


class BrowserSession:
    """Reutiliza o Chrome do sistema (janela visível) entre várias coletas.

    A inicialização é preguiçosa: o navegador só abre quando uma loja bloquear
    o `requests`. Lancado na mesma thread que o usa (cada worker cria o seu).
    """

    def __init__(self):
        self._pw = None
        self._browser = None
        self._page = None

    def _ensure(self):
        if self._browser is not None:
            return self._page
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise BlockedError(
                "Navegador não disponível: instale o playwright (pip install playwright)."
            ) from exc
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(channel="chrome", headless=False)
        self._page = self._browser.new_page(locale="pt-BR")
        return self._page

    def fetch(self, url, timeout=30000):
        page = self._ensure()
        page.goto(url, timeout=timeout, wait_until="load")
        page.wait_for_timeout(5000)
        content = page.content()
        if len(content) < MIN_HTML_LEN:
            # desafio intermitente (robot check): recarrega uma vez e espera mais
            try:
                page.reload(timeout=timeout, wait_until="load")
                page.wait_for_timeout(6000)
                content = page.content()
            except Exception:
                pass
        return content

    def close(self):
        for closer in (self._close_page, self._close_browser, self._stop_pw):
            try:
                closer()
            except Exception:
                pass

    def _close_page(self):
        if self._page is not None:
            self._page.close()
            self._page = None

    def _close_browser(self):
        if self._browser is not None:
            self._browser.close()
            self._browser = None

    def _stop_pw(self):
        if self._pw is not None:
            self._pw.stop()
            self._pw = None


def _requests_tree(url, timeout=15):
    response = requests.get(url, headers=HEADERS, timeout=timeout, verify=False)
    if response.status_code != 200:
        raise BlockedError(f"HTTP {response.status_code}")
    if len(response.content) < MIN_HTML_LEN:
        raise BlockedError("resposta pequena demais (provável desafio anti-bot)")
    try:
        return html.fromstring(response.content)
    except Exception as exc:
        raise BlockedError(f"HTML inválido: {exc}") from exc


def _parse_single(tree, url):
    result = {"nome": "", "preco": None, "loja": store_name(url)}

    ld = _json_ld(tree)
    if ld:
        if ld.get("name"):
            result["nome"] = ld["name"]
        if ld.get("price") is not None:
            result["preco"] = ld["price"]

    if not result["nome"] or result["preco"] is None:
        props = _og_meta(tree)
        if not result["nome"]:
            result["nome"] = props.get("og:title", "")
        if result["preco"] is None:
            for prop in OG_PRICE_PROPS:
                if props.get(prop):
                    result["preco"] = normalize_price(props[prop])
                    break

    if result["preco"] is None:
        result["preco"] = _store_price(tree, url)

    if not result["nome"]:
        result["nome"] = _page_title(tree)

    result["nome"] = _clean(result["nome"]) or "Produto sem nome"
    return result


def fetch_product(url, timeout=15, session=None):
    """Busca nome e preço atual de um produto.

    Tenta `requests` primeiro; se a loja bloquear (anti-bot), abre o Chrome do
    sistema (janela visível, via playwright) para aquela coleta. `session` permite
    reutilizar o mesmo navegador entre vários produtos (batch).
    """
    url = (url or "").strip()
    if not url:
        raise ValueError("URL vazia")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    if store_name(url) in UNSUPPORTED_STORES:
        raise ValueError("Magazine Luiza bloqueia acesso automatizado (anti-bot).")

    try:
        tree = _requests_tree(url, timeout)
        return _parse_single(tree, url)
    except BlockedError:
        pass

    if session is None:
        session = BrowserSession()
        owned = True
    else:
        owned = False
    try:
        content = session.fetch(url)
    except Exception as exc:
        raise ValueError(f"Não foi possível carregar a página da loja: {exc}") from exc
    finally:
        if owned:
            session.close()

    if not content or len(content) < MIN_HTML_LEN:
        raise ValueError("A página retornou um desafio de navegador.")
    try:
        tree = html.fromstring(content)
    except Exception as exc:
        raise ValueError(f"Página inválida: {exc}") from exc

    result = _parse_single(tree, url)
    if result["preco"] is None:
        raise ValueError("Não foi possível encontrar o preço do produto.")
    return result
