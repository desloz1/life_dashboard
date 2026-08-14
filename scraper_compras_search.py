"""Busca de produto pelo nome nas lojas (parsers de resultados + orquestração).

Reutiliza o motor em cascata do `scraper_compras_engine` (Fetcher e, se
necessário, `ScraplingSession`). Cada loja tem um parser dedicado, com fallback
genérico quando o seletor específico não acha algo.
"""

import json
import re
from urllib.parse import quote, quote_plus, urljoin

from scraper_compras_core import STORES, UNSUPPORTED_STORES, _clean, normalize_price
from scraper_compras_engine import _fetcher_fetch

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