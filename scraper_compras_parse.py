"""Parsing de páginas de produto (JSON-LD → Open Graph → seletor → genérico).

Recebe uma página (Selector) e devolve `{"nome", "preco", "loja"}`. Os
seletores de preço por loja referenciam funções deste módulo via
`STORES[store]["price"]` (definido no core).
"""

import json

from scraper_compras_core import _clean, _store_entry, normalize_price, store_name

OG_PRICE_PROPS = ("og:price:amount", "product:price:amount", "og:price:amount:usd")


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