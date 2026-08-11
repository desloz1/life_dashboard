import re

import requests

try:
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
    pass

import log
import scraper

logger = log.get_logger("life_dashboard.webcams")

# Câmeras ao vivo de Blumenau (SC). `stream` é um fallback conhecido; a cada
# carga o scraping da página tenta obter a URL de transmissão atualizada.
CAMERA_SOURCES = (
    {
        "id": "rio-itajai-acu",
        "name": "Rio Itajaí-Açú",
        "location": "Clube Náutico América · Beira-Rio",
        "provider": "BNU.tv",
        "page": "https://bnu.tv/blumenau/clube-nautico-america-remo-blumenau/",
        "stream": "https://5a8d73edc0407.streamlock.net:443/bnutv20/bnutv2004.stream/playlist.m3u8",
    },
    {
        "id": "av-beira-rio",
        "name": "Avenida Beira-Rio",
        "location": "Av. Presidente Castelo Branco · centro",
        "provider": "BNU.tv · Barbieri Painéis",
        "page": "https://bnu.tv/blumenau/camera-ao-vivo-barbieri-paineis-blumenau/",
        "stream": None,
    },
)


def _extract_stream(html):
    """Extrai a URL HLS da página: JSON-LD `contentUrl` ou `<video><source src>`."""
    match = re.search(r'"contentUrl"\s*:\s*"([^"]+\.m3u8[^"]*)"', html)
    if match:
        return match.group(1).replace("\\/", "/")
    match = re.search(r'<source[^>]+src=["\']([^"\']+\.m3u8[^"\']*)["\']', html, re.I)
    if match:
        return match.group(1)
    return None


def _extract_poster(html):
    """Extrai o poster/frame atual da transmissão (imagem estática de snapshot)."""
    match = re.search(r'<video[^>]+poster=["\']([^"\']+)["\']', html, re.I)
    if match:
        return match.group(1)
    match = re.search(r'property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html)
    if match:
        return match.group(1)
    return None


def _extract_name(html, fallback):
    match = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    if match:
        text = re.sub(r"<[^>]+>", "", match.group(1)).strip()
        if text:
            return text
    return fallback


def fetch_webcams():
    """Retorna as webcams de Blumenau com URL de stream/poster atualizados.

    Cada item: id, name, location, provider, page, stream (m3u8 ou None) e
    poster_url. Falha em uma fonte não derruba as demais.
    """
    cams = []
    for source in CAMERA_SOURCES:
        cam = dict(source)
        cam["poster_url"] = None
        cam["poster"] = None
        try:
            response = requests.get(source["page"], headers=scraper.HEADERS, timeout=25, verify=False)
            response.raise_for_status()
            html = response.text
            cam["name"] = _extract_name(html, source["name"])
            cam["stream"] = _extract_stream(html) or source.get("stream")
            cam["poster_url"] = _extract_poster(html)
        except Exception as exc:
            logger.warning("Falha ao carregar webcam %s: %s", source["page"], exc)
            cam["stream"] = source.get("stream")
        cams.append(cam)
    return cams
