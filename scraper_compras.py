"""Facade do engine de compras — API pública utilizada pela UI.

Responsabilidades:
- `scraper_compras_core`  → config, utilitários de preço/URL, detecção de desafio;
- `scraper_compras_parse` → parsing de página de produto;
- `scraper_compras_engine` → cascade Fetcher → navegador (`fetch_product`);
- `scraper_compras_search` → busca de produto pelo nome (`search_products`).

A UI importa as funções públicas daqui (ex.: `scraper_compras.fetch_product`).
"""

from scraper_compras_core import (  # noqa: F401
    STORES,
    UNSUPPORTED_STORES,
    BlockedError,
    normalize_price,
    store_name,
)
from scraper_compras_engine import ScraplingSession, fetch_product  # noqa: F401
from scraper_compras_search import (  # noqa: F401
    DEFAULT_SEARCH_LIMIT,
    search_products,
    searchable_stores,
)

__all__ = [
    "STORES",
    "UNSUPPORTED_STORES",
    "BlockedError",
    "normalize_price",
    "store_name",
    "ScraplingSession",
    "fetch_product",
    "DEFAULT_SEARCH_LIMIT",
    "search_products",
    "searchable_stores",
]