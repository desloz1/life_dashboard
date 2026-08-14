"""Workers (QThread) do Início (dashboard): notícias regionais e de tecnologia."""

from PySide6.QtCore import QThread, Signal

import log
import news
import scraper

logger = log.get_logger("life_dashboard.dashboard_workers")


class DashNewsWorker(QThread):
    finished_ok = Signal(list)
    failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        raw = []
        errors = []
        for source in scraper.SOURCES:
            if self.isInterruptionRequested():
                return
            try:
                raw.extend(scraper.fetch_news(source, limit=10))
            except Exception as exc:
                errors.append(f"{source}: {exc}")
                logger.warning("Falha ao buscar notícias de %s: %s", source, exc)
        if not raw:
            self.failed.emit("; ".join(errors) or "Nenhuma notícia carregada")
            return
        items = news.sort_by_date(raw, limit=10)
        if not self.isInterruptionRequested():
            self.finished_ok.emit(items)


class DashTechWorker(QThread):
    finished_ok = Signal(list)
    failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        try:
            raw = scraper.fetch_tech_news(limit=15)
        except Exception as exc:
            logger.warning("Falha ao buscar notícias de tecnologia: %s", exc)
            if not self.isInterruptionRequested():
                self.failed.emit(str(exc))
            return
        items = news.sort_by_date(raw, limit=10)
        if not self.isInterruptionRequested():
            self.finished_ok.emit(items)