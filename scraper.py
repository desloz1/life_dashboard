import re

import requests
from lxml import html

try:
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
    pass

NSC_URL = "https://www.nsctotal.com.br/cidades/blumenau"
INFORME_URL = "https://www.informeblumenau.com/"
AJNOTICIAS_URL = "https://ajnoticias.com.br/"
OBLUMENAUENSE_URL = "https://oblumenauense.com.br/"
NDMAIS_URL = "https://ndmais.com.br/blumenau/"
TECNOBLOG_URL = "https://tecnoblog.net/"

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
    response = requests.get(AJNOTICIAS_URL, headers=HEADERS, timeout=15, verify=False)
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


def _oblumenauense_image(module):
    for img in module.xpath(".//img"):
        for attr in ("src", "data-src", "data-lazy-src", "data-original"):
            value = (img.get(attr) or "").strip()
            if value and "no_thumb" not in value and not value.endswith(".gif"):
                return value
    return ""


def _iso_date(iso):
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})", iso or "")
    if not match:
        return ""
    year, month, day, hour, minute = match.groups()
    return "%s/%s/%s %s:%s" % (day, month, year, hour, minute)


def _fetch_oblumenauense(limit):
    response = requests.get(OBLUMENAUENSE_URL, headers=HEADERS, timeout=15, verify=False)
    response.raise_for_status()
    response.encoding = "utf-8"
    tree = html.fromstring(response.text)

    by_url = {}
    for module in tree.xpath('//div[contains(@class, "td_module")]'):
        title_link = module.xpath(".//h3/a")
        if not title_link:
            continue
        href = (title_link[0].get("href") or "").strip()
        title = _clean(title_link[0].text_content())
        if not href or not title:
            continue
        category_links = module.xpath('.//a[contains(@class, "td-post-category")]')
        category = _clean(category_links[0].text_content()) if category_links else ""
        raw_dates = [d.strip() for d in module.xpath(".//time/text()") if d.strip()]
        raw_datetimes = [d.strip() for d in module.xpath(".//time/@datetime") if d.strip()]
        if raw_dates:
            date = raw_dates[0]
        elif raw_datetimes:
            date = _iso_date(raw_datetimes[0])
        else:
            date = ""
        image = _bigger_image(_oblumenauense_image(module))

        entry = by_url.get(href)
        if entry is None:
            by_url[href] = {
                "title": title,
                "url": href,
                "image": image,
                "category": category or "Notícias",
                "date": date,
                "source": "O Blumenauense",
            }
        else:
            if (not entry["category"] or entry["category"] == "Notícias") and category:
                entry["category"] = category
            if not entry["date"] and date:
                entry["date"] = date
            if not entry["image"] and image:
                entry["image"] = image
    return list(by_url.values())[:limit]


def _path_category(url):
    match = re.search(r"://[^/]+/([^/]+)", url or "")
    if not match:
        return "Notícias"
    raw = match.group(1).lower().replace("-", " ")
    return raw.title()


def _ndmais_category(article):
    for cls in ("hat", "categoria"):
        links = article.xpath('.//a[contains(@class, "%s")]' % cls)
        if links:
            text = _clean(links[0].text_content())
            if text:
                return text
    return ""


def _ndmais_image(article):
    for img in article.xpath(".//img"):
        for attr in ("src", "data-src", "data-lazy-src"):
            value = (img.get(attr) or "").strip()
            if value:
                return value
    return ""


def _fetch_ndmais(limit):
    response = requests.get(NDMAIS_URL, headers=HEADERS, timeout=15)
    response.raise_for_status()
    response.encoding = "utf-8"
    tree = html.fromstring(response.text)

    by_url = {}
    for article in tree.xpath(
        '//article[not(ancestor::div[contains(@class, "swiper")])'
        ' and not(ancestor::*[@id="mais-acessadas-sidebar"])]'
    ):
        title_link = article.xpath(".//h1/a | .//h2/a | .//h3/a | .//h4/a")
        if not title_link:
            continue
        href = (title_link[0].get("href") or "").strip()
        title = _clean(title_link[0].text_content())
        if not href or not title:
            continue
        datetime_attr = article.xpath('.//time[@datetime]/@datetime')
        date = _iso_date(datetime_attr[0]) if datetime_attr else ""
        category = _ndmais_category(article)
        image = _bigger_image(_ndmais_image(article))

        entry = by_url.get(href)
        if entry is None:
            by_url[href] = {
                "title": title,
                "url": href,
                "image": image,
                "category": category or _path_category(href),
                "date": date,
                "source": "ND Mais",
            }
        else:
            if not entry["date"] and date:
                entry["date"] = date
            if not entry["image"] and image:
                entry["image"] = image
            if (not entry["category"] or entry["category"] == "Notícias") and category:
                entry["category"] = category
    return list(by_url.values())[:limit]


def _tecnoblog_image(article):
    for img in article.xpath(".//img"):
        for attr in ("data-src", "src", "data-lazy-src"):
            value = (img.get(attr) or "").strip()
            if value and not value.startswith("data:image"):
                return value
    return ""


def _tecnoblog_date(article):
    for time_el in article.xpath(".//time"):
        iso = (time_el.get("datetime") or "").strip()
        if iso:
            return _iso_date(iso)
    return ""


def _fetch_tecnoblog(limit):
    response = requests.get(TECNOBLOG_URL, headers=HEADERS, timeout=15)
    response.raise_for_status()
    tree = html.fromstring(response.content)

    items = []
    seen = set()
    for article in tree.xpath("//article"):
        heading = article.xpath(".//h2/a | .//h3/a | .//h2 | .//h3")
        if not heading:
            continue
        title = _clean(heading[0].text_content())
        if not title:
            continue
        links = article.xpath(".//a[contains(@href, 'tecnoblog.net')]")
        href = ""
        for link in links:
            candidate = (link.get("href") or "").strip()
            if candidate and "achados.tecnoblog.net" not in candidate:
                href = candidate
                break
        if not href or href in seen:
            continue
        seen.add(href)
        cat_links = article.xpath('.//span[contains(@class, "catname")] | .//a[contains(@class, "cat")]')
        category = _clean(cat_links[0].text_content()) if cat_links else "Tecnologia"
        items.append(
            {
                "title": title,
                "url": href,
                "image": _bigger_image(_tecnoblog_image(article)),
                "category": category or "Tecnologia",
                "date": _tecnoblog_date(article),
                "source": "TecnoBlog",
            }
        )
        if len(items) >= limit:
            return items
    return items


SOURCES = {
    "NSC Total": {"url": NSC_URL, "fetch": _fetch_nsc},
    "Informe Blumenau": {"url": INFORME_URL, "fetch": _fetch_informe},
    "AJ Notícias": {"url": AJNOTICIAS_URL, "fetch": _fetch_ajnoticias},
    "O Blumenauense": {"url": OBLUMENAUENSE_URL, "fetch": _fetch_oblumenauense},
    "ND Mais": {"url": NDMAIS_URL, "fetch": _fetch_ndmais},
}

TECH_SOURCES = {
    "TecnoBlog": {"url": TECNOBLOG_URL, "fetch": _fetch_tecnoblog},
}


def fetch_tech_news(limit=10):
    """Coleta as notícias de tecnologia mais recentes (TecnoBlog)."""
    return _fetch_tecnoblog(limit)


def fetch_news(source="NSC Total", limit=10):
    entry = SOURCES.get(source)
    if entry is None:
        raise ValueError(f"Fonte desconhecida: {source}")
    return entry["fetch"](limit)


def fetch_titles(limit=50):
    """Coleta títulos únicos das notícias de todas as fontes (mais recentes primeiro por fonte)."""
    titles = []
    seen = set()
    for source in SOURCES:
        try:
            items = SOURCES[source]["fetch"](limit)
        except Exception:
            continue
        for item in items:
            title = _clean(item.get("title"))
            if not title:
                continue
            key = title.lower()
            if key in seen:
                continue
            seen.add(key)
            titles.append(title)
            if len(titles) >= limit:
                return titles
    return titles


def save_daily_titles(limit=50, directory=None):
    """Gera o arquivo noticias_mes_dia_ano.txt com os títulos do dia. Retorna o caminho."""
    import datetime
    from pathlib import Path

    titles = fetch_titles(limit)
    base = Path(directory) if directory else Path(__file__).resolve().parent
    today = datetime.date.today()
    filename = f"noticias_{today.month:02d}_{today.day:02d}_{today.year}.txt"
    path = base / filename
    with open(path, "w", encoding="utf-8") as fh:
        for i, title in enumerate(titles, 1):
            fh.write(f"{i}. {title}\n")
    return str(path)
