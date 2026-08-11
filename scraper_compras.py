import json
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

OG_PRICE_PROPS = ("og:price:amount", "product:price:amount", "og:price:amount:usd")

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


def _json_ld(page):
    for script in page.xpath('//script[@type="application/ld+json"]'):
        text = _clean(str(script.text))
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


def _og_meta(page):
    props = {}
    for meta in page.xpath("//meta"):
        prop = (meta.attrib.get("property") or meta.attrib.get("name") or "").strip()
        if not prop or prop in props:
            continue
        value = (meta.attrib.get("content") or "").strip()
        if value:
            props[prop.lower()] = value
    return props


def _page_title(page):
    nodes = page.xpath("//title")
    return _clean(str(nodes[0].get_all_text())) if nodes else ""


def _amazon_price(page):
    # A Amazon emite vários `.a-offscreen` (títulos + preços); o primeiro pode
    # ser um título. Percorre até achar um nó que seja claramente um preço.
    for node in page.css(".a-offscreen", adaptive=True):
        text = _clean(str(node.text))
        if "R$" in text.upper():
            price = normalize_price(text)
            if price is not None:
                return price
    return None


def _ml_price(page):
    frac = page.css(".andes-money-amount__fraction", adaptive=True)
    if not frac:
        return None
    text = _clean(str(frac[0].text))
    cents = page.css(".andes-money-amount__cents", adaptive=True)
    if cents:
        text += "," + _clean(str(cents[0].text))
    return normalize_price(text)


def _store_price(page, url):
    name, entry = _store_entry(url)
    if not entry or not entry.get("price"):
        return None
    fn = globals().get(entry["price"])
    if fn is None:
        return None
    try:
        return fn(page)
    except Exception:
        return None


def _generic_price(page):
    """Fallback por padrão monetário: primo elemento com 'R$' e valor de preço plausível."""
    for node in page.css("span, p, div, b, strong")[:150]:
        text = _clean(str(node.get_all_text()))
        if "R$" not in text or len(text) > 40:
            continue
        price = normalize_price(text)
        if price is not None and price <= 200000:
            return price
    return None


def _parse_single(page, url):
    result = {"nome": "", "preco": None, "loja": store_name(url)}

    ld = _json_ld(page)
    if ld:
        if ld.get("name"):
            result["nome"] = ld["name"]
        if ld.get("price") is not None:
            result["preco"] = ld["price"]

    if not result["nome"] or result["preco"] is None:
        props = _og_meta(page)
        if not result["nome"]:
            result["nome"] = props.get("og:title", "")
        if result["preco"] is None:
            for prop in OG_PRICE_PROPS:
                if props.get(prop):
                    result["preco"] = normalize_price(props[prop])
                    break

    if result["preco"] is None:
        result["preco"] = _store_price(page, url)

    if result["preco"] is None:
        result["preco"] = _generic_price(page)

    if not result["nome"]:
        result["nome"] = _page_title(page)

    result["nome"] = _clean(result["nome"]) or "Produto sem nome"
    return result


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


# ---------------------------------------------------------------------------
# Engine em cascata (substitui requests + BrowserSession/playwright)
# ---------------------------------------------------------------------------

def _fetcher_fetch(url, timeout_ms):
    """Camada 1: HTTP estático com impersonação de TLS (curl_cffi via Scrapling)."""
    from scrapling.fetchers import Fetcher

    response = Fetcher.get(
        url,
        impersonate="chrome",
        stealthy_headers=True,
        verify=False,
        timeout=timeout_ms,
        follow_redirects=True,
        selector_config={"adaptive": True},
    )
    if response.status != 200:
        raise BlockedError(f"HTTP {response.status}")
    body = response.body or b""
    if len(body) < MIN_HTML_LEN:
        raise BlockedError("resposta pequena demais (provável desafio anti-bot)")
    page = _build_selector(body, url)
    if _is_challenge(page):
        raise BlockedError("desafio anti-bot detectado")
    return page


class ScraplingSession:
    """Sessão de navegador (Scrapling) reutilizada entre as coletas de uma batelada.

    Substitui o antigo `BrowserSession`. Inicialização preguiçosa (o navegador só
    abre quando o `Fetcher` é bloqueado), lançada na mesma thread que a usa (cada
    worker cria a sua) e reutilizada entre os produtos da batelada.

    Cascata interna:
      1) `DynamicSession` (Playwright, real Chrome) para páginas com JS;
      2) `StealthySession` (Patchright, real Chrome, Cloudflare) para anti-bot pesado.
    """

    def __init__(self, timeout_ms=30000):
        self._timeout_ms = timeout_ms
        self._dynamic = None
        self._stealth = None

    def fetch(self, url):
        try:
            return self._fetch_dynamic(url)
        except Exception:
            self._close_dynamic()
            return self._fetch_stealth(url)

    def _fetch_dynamic(self, url):
        if self._dynamic is None:
            from scrapling.fetchers import DynamicSession

            self._dynamic = DynamicSession(
                headless=True,
                real_chrome=True,
                network_idle=True,
                timeout=self._timeout_ms,
                selector_config={"adaptive": True},
            )
            self._dynamic.start()
        response = self._dynamic.fetch(url, timeout=self._timeout_ms)
        page = self._check_response(response, url)
        if _is_challenge(page):
            raise BlockedError("desafio detectado no navegador (dynamic)")
        return page

    def _fetch_stealth(self, url):
        if self._stealth is None:
            from scrapling.fetchers import StealthySession

            self._stealth = StealthySession(
                headless=True,
                real_chrome=True,
                solve_cloudflare=True,
                timezone_id="America/Sao_Paulo",
                timeout=self._timeout_ms,
                selector_config={"adaptive": True},
            )
            self._stealth.start()
        response = self._stealth.fetch(url, timeout=self._timeout_ms)
        return self._check_response(response, url)

    @staticmethod
    def _check_response(response, url):
        body = response.body or b""
        if len(body) < MIN_HTML_LEN:
            raise ValueError("A página retornou um desafio de navegador.")
        return _build_selector(body, url)

    def _close_dynamic(self):
        if self._dynamic is not None:
            try:
                self._dynamic.close()
            except Exception:
                pass
            self._dynamic = None

    def close(self):
        for sess_name in ("_dynamic", "_stealth"):
            sess = getattr(self, sess_name)
            if sess is not None:
                try:
                    sess.close()
                except Exception:
                    pass
                setattr(self, sess_name, None)


def fetch_product(url, timeout=15, session=None):
    """Busca nome e preço atual de um produto.

    Estratégia em cascata (substitui o antigo requests + BrowserSession):
      1) `Fetcher` (HTTP estático com impersonação, sem abrir navegador);
      2) `ScraplingSession` (navegador real headless, reutilizado na batelada)
         com `DynamicSession` e, se houver desafio, `StealthySession`.
    `session` permite reutilizar a mesma sessão de navegador entre vários
    produtos (batch) — não precisa ser fechada aqui.
    """
    url = (url or "").strip()
    if not url:
        raise ValueError("URL vazia")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    if store_name(url) in UNSUPPORTED_STORES:
        raise ValueError("Magazine Luiza bloqueia acesso automatizado (anti-bot).")

    timeout_ms = max(1, int((timeout or 15) * 1000))

    try:
        page = _fetcher_fetch(url, timeout_ms)
        return _parse_single(page, url)
    except BlockedError:
        pass
    except Exception as exc:
        raise ValueError(f"Não foi possível carregar a página da loja: {exc}") from exc

    owned = session is None
    if session is None:
        session = ScraplingSession(timeout_ms=timeout_ms)
    try:
        page = session.fetch(url)
    except Exception as exc:
        raise ValueError(f"Não foi possível carregar a página da loja: {exc}") from exc
    finally:
        if owned:
            session.close()

    result = _parse_single(page, url)
    if result["preco"] is None:
        raise ValueError("Não foi possível encontrar o preço do produto.")
    return result
