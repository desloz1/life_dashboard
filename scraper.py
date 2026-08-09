import re

import requests
from lxml import html

NSC_URL = "https://www.nsctotal.com.br/cidades/blumenau"
INFORME_URL = "https://www.informeblumenau.com/"
AJNOTICIAS_URL = "https://ajnoticias.com.br/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
}

NSC_NEWS_SECTIONS = ("bwgr-nsc-n2", "bwgr-n3", "bwgr-n6", "bwgr-n10")

NSC_CATEGORY_NAMES = {
    "colunista": "Coluna",
    "cotidiano": "Cotidiano",
    "seguranca": "Segurança",
    "economia": "Economia",
    "transito": "Trânsito",
    "educacao": "Educação",
    "saude": "Saúde",
    "politica": "Política",
    "infraestrutura": "Infraestrutura",
    "justica": "Justiça",
    "ciencia-e-tecnologia": "Ciência & Tecnologia",
    "entretenimento": "Entretenimento",
    "esportes": "Esportes",
    "esporte": "Esportes",
    "meio-ambiente": "Meio Ambiente",
    "turismo": "Turismo",
    "gastronomia": "Gastronomia",
    "cultura": "Cultura",
    "agro": "Agro",
    "imoveis": "Imóveis",
}

INFORME_SKIP_CATEGORIES = {"destaques", "coluna", "coluna b", "noticias"}

INFORME_CATEGORY_NAMES = {
    "politica": "Política",
    "cidade": "Cidade",
    "geral": "Geral",
    "saude": "Saúde",
    "educacao": "Educação",
    "esporte": "Esporte",
    "cultura": "Cultura",
    "economia": "Economia",
    "seguranca": "Segurança",
    "entretenimento": "Entretenimento",
}


def _clean(text):
    return (text or "").replace("\ufeff", "").strip()


def _category_from_url(url):
    path = url.split("nsctotal.com.br/", 1)[-1].strip("/")
    parts = path.split("/")
    if not parts:
        return "Notícias"
    raw = parts[0].lower()
    if raw == "colunista" and len(parts) >= 2:
        raw = parts[1].lower()
    return NSC_CATEGORY_NAMES.get(raw, raw.replace("-", " ").title())


def _image_from_article(article):
    for img in article.xpath(".//img"):
        for attr in ("src", "data-src", "data-lazy-src"):
            value = (img.get(attr) or "").strip()
            if value:
                return value
    return ""


def _fetch_nsc(limit):
    response = requests.get(NSC_URL, headers=HEADERS, timeout=15)
    response.raise_for_status()
    tree = html.fromstring(response.content)

    items = []
    seen = set()
    for section in tree.xpath("//section"):
        classes = section.get("class") or ""
        if not any(k in classes for k in NSC_NEWS_SECTIONS):
            continue
        for article in section.xpath(".//article"):
            link = article.xpath(".//h2/a | .//h3/a | .//h4/a")
            if not link:
                continue
            href = (link[0].get("href") or "").strip()
            title = _clean(link[0].text_content())
            if not href or not title or href in seen:
                continue
            seen.add(href)
            items.append(
                {
                    "title": title,
                    "url": href,
                    "image": _bigger_image(_image_from_article(article)),
                    "category": _category_from_url(href),
                    "date": "",
                    "source": "NSC Total",
                }
            )
            if len(items) >= limit:
                return items
    return items


def _bigger_image(url):
    return re.sub(r"-\d+x\d+(\.[A-Za-z]+)$", r"\1", url)


def _informe_category(article):
    classes = article.get("class") or ""
    for token in classes.split():
        if token.startswith("category-"):
            raw = token[len("category-"):].strip("_").replace("_", " ").title()
            if raw.lower() not in INFORME_SKIP_CATEGORIES:
                return INFORME_CATEGORY_NAMES.get(raw.lower(), raw)
    return "Notícias"


def _informe_title_link(article):
    heading = article.xpath(".//h1/a | .//h2/a | .//h3/a | .//h4/a")
    if heading:
        title = _clean(heading[0].text_content())
        href = (heading[0].get("href") or "").strip()
        if title and href:
            return title, href
    image_link = article.xpath(".//a[.//img]")
    if image_link:
        title = _clean(image_link[0].get("title"))
        href = (image_link[0].get("href") or "").strip()
        if title and href:
            return title, href
    return "", ""


def _informe_date(article):
    spans = article.xpath('.//span[contains(@class, "entry-meta-date")]//text()')
    return "".join(spans).strip()


def _fetch_informe(limit):
    response = requests.get(INFORME_URL, headers=HEADERS, timeout=15)
    response.raise_for_status()
    tree = html.fromstring(response.content)

    items = []
    seen = set()
    for article in tree.xpath("//article"):
        title, href = _informe_title_link(article)
        if not title or not href or href in seen:
            continue
        seen.add(href)
        items.append(
            {
                "title": title,
                "url": href,
                "image": _bigger_image(_image_from_article(article)),
                "category": _informe_category(article),
                "date": _informe_date(article),
                "source": "Informe Blumenau",
            }
        )
        if len(items) >= limit:
            return items
    return items


def _aj_image(link):
    for img in link.xpath(".//img"):
        value = (img.get("data-src") or "").strip()
        if value:
            return value
        value = (img.get("src") or "").strip()
        if value and "pre-img.jpg" not in value:
            return value
    return ""


def _fetch_ajnoticias(limit):
    response = requests.get(AJNOTICIAS_URL, headers=HEADERS, timeout=15)
    response.raise_for_status()
    response.encoding = "utf-8"
    tree = html.fromstring(response.text)

    by_id = {}
    for link in tree.xpath("//a[contains(@href, '/noticia/')]"):
        match = re.search(r"/noticia/(\d+)/", link.get("href") or "")
        if not match:
            continue
        aid = int(match.group(1))
        by_id.setdefault(aid, link)

    items = []
    for aid in sorted(by_id, reverse=True):
        link = by_id[aid]
        headings = link.xpath(".//h3")
        if not headings:
            continue
        title = _clean(headings[0].text_content())
        href = (link.get("href") or "").strip()
        if not title or not href:
            continue
        category = link.xpath(
            './/span[contains(@class, "dest-chapeu")'
            ' or contains(@class, "chapeu-slide")'
            ' or contains(@class, "chapeu-ultimas")]'
        )
        date = link.xpath(
            './/span[contains(@class, "data-lista-home")'
            ' or contains(@class, "data-ultimas")]'
        )
        items.append(
            {
                "title": title,
                "url": href,
                "image": _aj_image(link),
                "category": _clean(category[0].text_content()) if category else "Notícias",
                "date": _clean(date[0].text_content()) if date else "",
                "source": "AJ Notícias",
            }
        )
        if len(items) >= limit:
            return items
    return items


SOURCES = {
    "NSC Total": {"url": NSC_URL, "fetch": _fetch_nsc},
    "Informe Blumenau": {"url": INFORME_URL, "fetch": _fetch_informe},
    "AJ Notícias": {"url": AJNOTICIAS_URL, "fetch": _fetch_ajnoticias},
}


def fetch_news(source="NSC Total", limit=10):
    entry = SOURCES.get(source)
    if entry is None:
        raise ValueError(f"Fonte desconhecida: {source}")
    return entry["fetch"](limit)
