import json
import re
from urllib.parse import quote, quote_plus, urljoin, urlparse

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


# ---------------------------------------------------------------------------
# Busca de produto pelo nome nas lojas
# ---------------------------------------------------------------------------

DEFAULT_SEARCH_LIMIT = 8


def searchable_stores():
    """Lojas pesquisáveis por nome (todas as suportadas, exceto as bloqueadas)."""
    return [name for name in STORES if name not in UNSUPPORTED_STORES]


def _search_url(store, query):
    if store == "Amazon":
        return "https://www.amazon.com.br/s?k=" + quote_plus(query)
    if store == "Mercado Livre":
        slug = re.sub(r"\s+", "-", re.sub(r"[^\w\s-]", "", query.strip().lower()))
        return "https://lista.mercadolivre.com.br/" + quote(slug, safe="-")
    if store == "Kabum":
        return "https://www.kabum.com.br/busca/" + quote_plus(query)
    if store == "Casas Bahia":
        return "https://www.casasbahia.com.br/busca?q=" + quote_plus(query)
    if store == "Americanas":
        return "https://www.americanas.com.br/busca/" + quote_plus(query)
    if store == "Pichau":
        return "https://www.pichau.com.br/search?q=" + quote_plus(query)
    if store == "Terabyte":
        return "https://www.terabyteshop.com.br/busca?str=" + quote_plus(query)
    return ""


def _search_amazon(page, url, limit):
    results = []
    seen = set()
    for card in page.css("div[data-component-type='s-search-result']", adaptive=True):
        if len(results) >= limit:
            break
        h2 = card.css("h2", adaptive=True)
        if not h2:
            continue
        title = _clean(str(h2[0].get_all_text()))
        if not title:
            continue
        href = ""
        node = h2[0].parent
        if node is not None and getattr(node, "tag", "") == "a":
            href = node.attrib.get("href") or ""
        if not href:
            for a in card.css("a[href]", adaptive=True):
                h = a.attrib.get("href", "")
                if "/dp/" in h or "/gp/" in h:
                    href = h
                    break
        if not href:
            continue
        low = href.lower()
        if "/sspa/click" in low or "sponsored" in low:
            continue
        full = urljoin(url, href)
        if full in seen:
            continue
        seen.add(full)
        preco = None
        off = card.css(".a-price .a-offscreen", adaptive=True)
        if off:
            preco = normalize_price(_clean(str(off[0].get_all_text())))
        results.append({"nome": title, "url": full, "preco": preco})
    return results


def _search_ml(page, url, limit):
    results = []
    seen = set()
    for card in page.css("li.ui-search-layout__item", adaptive=True):
        if len(results) >= limit:
            break
        anchor = card.css("a.ui-search-link", adaptive=True)
        if not anchor:
            anchor = card.css("a", adaptive=True)
        if not anchor:
            continue
        href = (anchor[0].attrib.get("href") or "").strip()
        title = ""
        title_node = card.css(".ui-search-item__title", adaptive=True)
        if title_node:
            title = _clean(str(title_node[0].get_all_text()))
        if not href or not title:
            continue
        full = urljoin(url, href)
        if full in seen:
            continue
        seen.add(full)
        preco = None
        frac = card.css(".andes-money-amount__fraction", adaptive=True)
        if frac:
            text = _clean(str(frac[0].get_all_text()))
            cents = card.css(".andes-money-amount__cents", adaptive=True)
            if cents:
                text += "," + _clean(str(cents[0].get_all_text()))
            preco = normalize_price(text)
        results.append({"nome": title, "url": full, "preco": preco})
    return results


def _next_data(page):
    for node in page.xpath('//script[@id="__NEXT_DATA__"]'):
        text = _clean(str(getattr(node, "text", None) or ""))
        if not text:
            continue
        try:
            return json.loads(text)
        except ValueError:
            return None
    return None


def _search_kabum(page, url, limit):
    results = []
    seen = set()

    # A Kabum é um SPA Next.js: os produtos estão no bloco __NEXT_DATA__.
    data = _next_data(page)
    if data:
        try:
            items = data["props"]["pageProps"]["data"]["catalogServer"]["data"]
        except (KeyError, TypeError):
            items = []
        for it in items or []:
            if len(results) >= limit:
                break
            if not isinstance(it, dict):
                continue
            name = _clean(it.get("name"))
            code = it.get("code")
            if not name or not code:
                continue
            preco = None
            for key in ("priceWithDiscount", "price"):
                val = it.get(key)
                if val not in (None, ""):
                    preco = normalize_price(val)
                    if preco is not None:
                        break
            full = "https://www.kabum.com.br/produto/" + str(code)
            if it.get("friendlyName"):
                full += "/" + str(it["friendlyName"])
            if full in seen:
                continue
            seen.add(full)
            results.append({"nome": name, "url": full, "preco": preco})
        if results:
            return results

    # Fallback HTML caso o layout volte a ser renderizado no servidor.
    for card in page.css("div.productCard", adaptive=True):
        if len(results) >= limit:
            break
        anchor = card.css("a", adaptive=True)
        if not anchor:
            continue
        href = (anchor[0].attrib.get("href") or "").strip()
        if not href:
            continue
        full = urljoin(url, href)
        if full in seen:
            continue
        title = ""
        img = card.css("img", adaptive=True)
        if img:
            title = _clean(img[0].attrib.get("alt", ""))
        if not title:
            name_el = card.css(".nameCard", adaptive=True)
            if name_el:
                title = _clean(str(name_el[0].get_all_text()))
        if not title:
            continue
        seen.add(full)
        preco = None
        price_el = card.css(".priceCard", adaptive=True)
        if price_el:
            preco = normalize_price(_clean(str(price_el[0].get_all_text())))
        results.append({"nome": title, "url": full, "preco": preco})
    return results


def _search_via(page, url, limit):
    """Casas Bahia / Americanas (plataforma VIA) e outras com card `[data-testid=product-card]`."""
    results = []
    seen = set()
    for card in page.css(
        "a[data-testid='product-card'], div[data-testid='product-card'], a[data-testid='ProductCard']",
        adaptive=True,
    ):
        if len(results) >= limit:
            break
        href = (card.attrib.get("href") or "").strip()
        if not href:
            continue
        full = urljoin(url, href)
        if full in seen:
            continue
        title = ""
        h3 = card.css("h3", adaptive=True)
        if h3:
            title = _clean(str(h3[0].get_all_text()))
        if not title:
            title = _clean(str(card.get_all_text()))
        if not title:
            continue
        seen.add(full)
        preco = None
        for el in card.css(
            "[data-testid='product-price'], [data-testid='productPrice'], .money",
            adaptive=True,
        ):
            text = _clean(str(el.get_all_text()))
            if "R$" in text:
                preco = normalize_price(text)
                if preco is not None:
                    break
        results.append({"nome": title, "url": full, "preco": preco})
    return results


def _search_pichau(page, url, limit):
    results = []
    seen = set()
    for card in page.css(
        ".product-item, .productItem, div[class*='product-item']", adaptive=True
    ):
        if len(results) >= limit:
            break
        anchor = card.css("a", adaptive=True)
        if not anchor:
            continue
        href = (anchor[0].attrib.get("href") or "").strip()
        if not href:
            continue
        full = urljoin(url, href)
        if full in seen:
            continue
        title = ""
        for sel in (".product-title", "h2", "h3"):
            node = card.css(sel, adaptive=True)
            if not node:
                continue
            title = _clean(str(node[0].get_all_text()))
            break
        if not title:
            img = card.css("img", adaptive=True)
            if img:
                title = _clean(img[0].attrib.get("alt", ""))
        if not title:
            continue
        seen.add(full)
        preco = None
        for el in card.css(".product-price, .price, .prodVal", adaptive=True):
            text = _clean(str(el.get_all_text()))
            if "R$" in text:
                preco = normalize_price(text)
                if preco is not None:
                    break
        results.append({"nome": title, "url": full, "preco": preco})
    return results


def _search_terabyte(page, url, limit):
    results = []
    seen = set()
    for card in page.css(
        ".commerce_columns_item_inner, .commerce_columns_item", adaptive=True
    ):
        if len(results) >= limit:
            break
        anchor = card.css("a", adaptive=True)
        if not anchor:
            continue
        href = (anchor[0].attrib.get("href") or "").strip()
        if not href:
            continue
        full = urljoin(url, href)
        if full in seen:
            continue
        title = ""
        for sel in (".com-title", "h2", "h3"):
            node = card.css(sel, adaptive=True)
            if not node:
                continue
            title = _clean(str(node[0].get_all_text()))
            break
        if not title:
            img = card.css("img", adaptive=True)
            if img:
                title = _clean(img[0].attrib.get("alt", ""))
        if not title:
            continue
        seen.add(full)
        preco = None
        for el in card.css(".com-preco, strong", adaptive=True):
            text = _clean(str(el.get_all_text()))
            if "R$" in text:
                preco = normalize_price(text)
                if preco is not None:
                    break
        results.append({"nome": title, "url": full, "preco": preco})
    return results


def _nearby_price(node):
    for el in node.css("span, b, strong, p, div")[:60]:
        text = _clean(str(el.get_all_text()))
        if "R$" in text and len(text) <= 40:
            price = normalize_price(text)
            if price is not None and price <= 200000:
                return price
    return None


def _search_generic(page, url, limit):
    """Fallback: âncoras com texto semelhante a produto + preço perto (R$)."""
    results = []
    seen = set()
    for anchor in page.css("a[href]", adaptive=True)[:300]:
        if len(results) >= limit:
            break
        href = (anchor.attrib.get("href") or "").strip()
        title = _clean(str(anchor.get_all_text()))
        if not href or not title or len(title) < 10:
            continue
        low = href.lower()
        if low.startswith(("javascript:", "mailto:", "tel:", "#")):
            continue
        if any(part in low for part in ("/busca", "/buscar", "/carrinho",
                                        "/login", "/conta", "/minha-conta",
                                        "/cupom", "/categorias", "/ofertas")):
            continue
        full = urljoin(url, href)
        if not full.startswith(("http://", "https://")):
            continue
        key = (full, title)
        if key in seen:
            continue
        seen.add(key)
        preco = None
        for anc in anchor.iterancestors():
            found = _nearby_price(anc)
            if found is not None:
                preco = found
                break
        results.append({"nome": title, "url": full, "preco": preco})
    return results


def _search_results(page, url, limit, store):
    if store == "Amazon":
        return _search_amazon(page, url, limit)
    if store == "Mercado Livre":
        return _search_ml(page, url, limit)
    if store == "Kabum":
        return _search_kabum(page, url, limit)
    if store in ("Casas Bahia", "Americanas"):
        return _search_via(page, url, limit)
    if store == "Pichau":
        return _search_pichau(page, url, limit)
    if store == "Terabyte":
        return _search_terabyte(page, url, limit)
    return _search_generic(page, url, limit)


def search_products(query, stores=None, limit_per_store=None, timeout=15,
                    session=None, progress=None):
    """Pesquisa um produto pelo nome nas lojas e devolve os resultados.

    Usa o mesmo motor em cascata do `fetch_product`: `Fetcher` (rápido, sem
    abrir navegador) e, se a loja bloquear, uma `ScraplingSession` (que deve
    ser criada na mesma thread do chamador e é reutilizada entre lojas).
    `progress(store)` (opcional) recebe o nome de cada loja antes da consulta.

    Retorna uma lista de `{"nome", "url", "loja", "preco"}` (preco pode ser None
    quando a loja não expõe o valor no resultado da busca).
    """
    query = (query or "").strip()
    if not query:
        return []
    if stores is None:
        stores = searchable_stores()
    limit = limit_per_store or DEFAULT_SEARCH_LIMIT
    timeout_ms = max(1, int((timeout or 15) * 1000))

    results = []
    seen = set()
    for store in stores:
        if store in UNSUPPORTED_STORES:
            continue
        url = _search_url(store, query)
        if not url:
            continue
        if progress:
            progress(store)
        items = []
        page = None
        try:
            page = _fetcher_fetch(url, timeout_ms)
        except Exception:
            page = None
        if page is not None:
            try:
                items = _search_results(page, url, limit, store)
            except Exception:
                items = []
        # Se o Fetcher não achou nada (ex.: página que renderiza por JS), sobe
        # para o navegador (DynamicSession/StealthySession) e tenta de novo.
        if not items and session is not None:
            try:
                page = session.fetch(url)
            except Exception:
                page = None
            if page is not None:
                try:
                    items = _search_results(page, url, limit, store)
                except Exception:
                    items = []
        for item in items:
            if not item.get("url"):
                continue
            item["loja"] = store
            item.setdefault("preco", None)
            key = (store, item["url"])
            if key in seen:
                continue
            seen.add(key)
            results.append(item)
    return results
