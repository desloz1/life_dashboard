"""Workers (QThread) da aba Compras: lookup de produto, atualização de preços e busca web."""

from PySide6.QtCore import QThread, Signal

import log
import scraper_compras

logger = log.get_logger("life_dashboard.compras_workers")


class LookupWorker(QThread):
    found = Signal(dict)
    failed = Signal(str)

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self._url = url

    def run(self):
        try:
            result = scraper_compras.fetch_product(self._url)
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.found.emit(result)


class PriceWorker(QThread):
    finished = Signal(int, int)  # (ok, falhas)

    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self._ids = [p.id for p in manager.products]

    def run(self):
        ok = 0
        fail = 0
        session = scraper_compras.ScraplingSession()
        try:
            for pid in self._ids:
                if self.isInterruptionRequested():
                    break
                product = self.manager.get(pid)
                if product is None:
                    continue
                try:
                    result = scraper_compras.fetch_product(product.url, session=session)
                    if result.get("nome"):
                        product.nome = result["nome"]
                    if result.get("loja"):
                        product.loja = result["loja"]
                    self.manager.update_price(pid, result.get("preco"))
                    ok += 1
                except Exception as exc:
                    logger.warning("Falha ao coletar preço de %s: %s", product.url, exc)
                    fail += 1
        finally:
            session.close()
        if not self.isInterruptionRequested():
            self.finished.emit(ok, fail)


class SearchWorker(QThread):
    progress = Signal(str)
    results = Signal(list)
    finished = Signal(int)

    def __init__(self, query, stores, limit=8, parent=None):
        super().__init__(parent)
        self._query = query
        self._stores = stores
        self._limit = limit

    def run(self):
        session = scraper_compras.ScraplingSession(timeout_ms=15000)
        found = []
        try:
            found = scraper_compras.search_products(
                self._query,
                stores=self._stores,
                limit_per_store=self._limit,
                timeout=12,
                session=session,
                progress=lambda store: self.progress.emit(f"Pesquisando em {store}…"),
            )
        except Exception as exc:
            logger.warning("Erro na busca de produtos: %s", exc)
        finally:
            session.close()
        if not self.isInterruptionRequested():
            self.results.emit(found)
            self.finished.emit(len(found))