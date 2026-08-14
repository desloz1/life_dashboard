"""Engine em cascata do scraper de compras (Fetcher → navegador).

Camada 1: `Fetcher` (HTTP estático com impersonação de TLS, sem abrir navegador).
Camada 2: `ScraplingSession` (navegador real headless, reutilizado na batelada)
com `DynamicSession` e, se houver desafio, `StealthySession`.
"""

from scraper_compras_core import (
    MIN_HTML_LEN,
    UNSUPPORTED_STORES,
    BlockedError,
    _build_selector,
    _is_challenge,
    store_name,
)
from scraper_compras_parse import _parse_single


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

    Inicialização preguiçosa (o navegador só abre quando o `Fetcher` é bloqueado),
    lançada na mesma thread que a usa (cada worker cria a sua) e reutilizada entre
    os produtos da batelada.

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

    Estratégia em cascata:
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