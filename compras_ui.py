import datetime

import qtawesome as qta
from PySide6.QtCore import QSize, Qt, QThread, QUrl, Signal
from PySide6.QtGui import QCursor, QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

import common
import compras
import log
import scraper_compras
import theme

logger = log.get_logger("life_dashboard.compras_ui")


def format_price(value):
    if value is None:
        return "—"
    return "R$ {:,.2f}".format(value).replace(",", "X").replace(".", ",").replace("X", ".")


def format_datetime(iso):
    if not iso:
        return ""
    try:
        dt = datetime.datetime.fromisoformat(iso)
    except (ValueError, TypeError):
        return ""
    return dt.strftime("%d/%m %H:%M")


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


class SearchResultRow(QFrame):
    open_requested = Signal(str)
    add_requested = Signal(dict)

    def __init__(self, result, parent=None):
        super().__init__(parent)
        self.result = result
        self.added = False
        self.setObjectName("webSearchRow")
        common.make_shadow(self, y=3, blur=16)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 12, 8)
        layout.setSpacing(10)

        icon = QLabel()
        icon.setObjectName("prodIcon")
        icon.setPixmap(qta.icon("fa5s.shopping-bag", color=theme.ACCENT).pixmap(20, 20))
        layout.addWidget(icon)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        self.title = QLabel(result["nome"])
        self.title.setObjectName("webSearchTitle")
        self.title.setWordWrap(True)
        self.title.setToolTip(result["nome"])
        text_col.addWidget(self.title)

        meta = QHBoxLayout()
        meta.setSpacing(8)
        badge = QLabel(result.get("loja", ""))
        badge.setObjectName("newsSource")
        meta.addWidget(badge)
        price_lbl = QLabel()
        price_lbl.setObjectName("prodMeta")
        if result.get("preco") is not None:
            price_lbl.setText(format_price(result["preco"]))
        else:
            price_lbl.setText("preço não encontrado")
        meta.addWidget(price_lbl)
        meta.addStretch()
        text_col.addLayout(meta)
        layout.addLayout(text_col, 1)

        self.price = QLabel(format_price(result.get("preco")))
        self.price.setObjectName("prodPrice")
        if result.get("preco") is None:
            self.price.setProperty("missing", True)
            self.price.style().unpolish(self.price)
            self.price.style().polish(self.price)
        self.price.setMinimumWidth(100)
        self.price.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.price)

        self.add_btn = QPushButton("＋ Adicionar")
        self.add_btn.setObjectName("secondaryBtn")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self._request_add)
        open_btn = QToolButton()
        open_btn.setObjectName("cardBtn")
        open_btn.setIcon(qta.icon("fa5s.external-link-alt", color=theme.ACCENT))
        open_btn.setIconSize(QSize(14, 14))
        open_btn.setFixedSize(24, 24)
        open_btn.setToolTip("Abrir na loja")
        open_btn.clicked.connect(lambda: self.open_requested.emit(result["url"]))
        layout.addWidget(self.add_btn)
        layout.addWidget(open_btn)

    def mark_added(self, already=False):
        self.added = True
        self.add_btn.setEnabled(False)
        self.add_btn.setText("Já acompanhado" if already else "Adicionado ✓")
        self.add_btn.setObjectName("addBtnDone")
        self.add_btn.style().unpolish(self.add_btn)
        self.add_btn.style().polish(self.add_btn)

    def _request_add(self):
        if not self.added:
            self.add_requested.emit(dict(self.result))


class SearchProductsDialog(QDialog):
    def __init__(self, add_callback, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Buscar produto nas lojas")
        self.setMinimumWidth(680)
        self._worker = None
        self._rows = []
        self._add_callback = add_callback

        root = QVBoxLayout(self)
        root.setSpacing(10)

        query_row = QHBoxLayout()
        self.query_edit = QLineEdit()
        self.query_edit.setObjectName("newsSearch")
        self.query_edit.setPlaceholderText("ex.: teclado mecânico, monitor 27…")
        self.query_edit.returnPressed.connect(self._start_search)
        self.search_btn = QPushButton(" Buscar")
        self.search_btn.setObjectName("refreshBtn")
        self.search_btn.setIcon(qta.icon("fa5s.search", color="#ffffff"))
        self.search_btn.setIconSize(QSize(14, 14))
        self.search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.search_btn.clicked.connect(self._start_search)
        query_row.addWidget(self.query_edit, 1)
        query_row.addWidget(self.search_btn)
        root.addLayout(query_row)

        stores_row = QHBoxLayout()
        stores_row.setSpacing(10)
        label_store = QLabel("Lojas:")
        label_store.setObjectName("prodMeta")
        stores_row.addWidget(label_store)
        self.store_checks = {}
        default_checked = {"Amazon", "Mercado Livre", "Kabum"}
        for store in scraper_compras.searchable_stores():
            chk = QCheckBox(store)
            chk.setChecked(store in default_checked)
            chk.setObjectName("searchStoreCheck")
            self.store_checks[store] = chk
            stores_row.addWidget(chk)
        stores_row.addStretch()
        root.addLayout(stores_row)

        self.status = QLabel("")
        self.status.setObjectName("status")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setObjectName("scrollArea")
        self.list_host = QWidget()
        self.list_layout = QVBoxLayout(self.list_host)
        self.list_layout.setContentsMargins(6, 0, 6, 6)
        self.list_layout.setSpacing(8)
        self.list_layout.addStretch()
        self.scroll.setWidget(self.list_host)
        root.addWidget(self.scroll, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self.rejected.connect(self.shutdown)

    def _selected_stores(self):
        return [name for name, chk in self.store_checks.items() if chk.isChecked()]

    def _start_search(self):
        query = self.query_edit.text().strip()
        if not query:
            self.status.setText("Informe o nome do produto primeiro.")
            return
        stores = self._selected_stores()
        if not stores:
            self.status.setText("Marque pelo menos uma loja para pesquisar.")
            return
        if self._worker is not None and self._worker.isRunning():
            return
        self._clear_results()
        self.search_btn.setEnabled(False)
        self.query_edit.setEnabled(False)
        self.status.setText("Iniciando busca…")
        self._worker = SearchWorker(query, stores, limit=8, parent=self)
        self._worker.progress.connect(self.status.setText)
        self._worker.results.connect(self._on_results)
        self._worker.finished.connect(self._on_search_done)
        self._worker.start()

    def _clear_results(self):
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._rows = []

    def _on_results(self, results):
        for result in results:
            row = SearchResultRow(result)
            row.open_requested.connect(self._open_link)
            row.add_requested.connect(self._on_add)
            self.list_layout.insertWidget(self.list_layout.count() - 1, row)
            self._rows.append(row)

    def _on_search_done(self, total):
        self.search_btn.setEnabled(True)
        self.query_edit.setEnabled(True)
        if not total:
            self.status.setText(
                "Nenhum resultado encontrado. Muitas lojas bloqueiam acessos "
                "automatizados (anti-bot); tente outra palavra-chave ou outra loja."
            )
        else:
            self.status.setText(f"{total} resultado{'s' if total != 1 else ''} "
                                "encontrado(s) — clique em \"＋ Adicionar\" para acompanhar.")

    def _on_add(self, result):
        added = self._add_callback(result)
        for row in self._rows:
            if row.result.get("url") == result["url"]:
                row.mark_added(not added)
                break

    def _open_link(self, url):
        QDesktopServices.openUrl(QUrl(url))

    def shutdown(self):
        if self._worker is not None:
            self._worker.requestInterruption()
            self._worker.wait(3000)


class AddProductDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Adicionar produto")
        self.setMinimumWidth(480)
        self._lookup = None
        self.lookup_done = False
        self._nome = ""
        self._loja = ""
        self._preco = None

        form = QFormLayout(self)
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://www.loja.com.br/produto/…")
        form.addRow("URL do produto:", self.url_edit)
        self.target_edit = QLineEdit()
        self.target_edit.setPlaceholderText("ex.: 150,00 (opcional)")
        form.addRow("Preço alvo:", self.target_edit)

        lookup_row = QHBoxLayout()
        self.lookup_btn = QPushButton("Buscar")
        self.lookup_btn.setObjectName("refreshBtn")
        self.lookup_btn.setIcon(qta.icon("fa5s.search", color="#ffffff"))
        self.lookup_btn.setIconSize(QSize(14, 14))
        self.lookup_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lookup_btn.clicked.connect(self._do_lookup)
        self.lookup_status = QLabel("")
        self.lookup_status.setObjectName("prodMeta")
        self.lookup_status.setWordWrap(True)
        lookup_row.addWidget(self.lookup_btn)
        lookup_row.addWidget(self.lookup_status, 1)
        form.addRow("", lookup_row)

        self.result_label = QLabel("")
        self.result_label.setObjectName("prodMeta")
        self.result_label.setWordWrap(True)
        form.addRow(self.result_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _do_lookup(self):
        url = self.url_edit.text().strip()
        if not url:
            self.lookup_status.setText("Informe a URL primeiro.")
            return
        if self._lookup is not None and self._lookup.isRunning():
            return
        self.lookup_btn.setEnabled(False)
        self.lookup_status.setText("Buscando…")
        self._lookup = LookupWorker(url)
        self._lookup.found.connect(self._on_found)
        self._lookup.failed.connect(self._on_failed)
        self._lookup.finished.connect(lambda: self.lookup_btn.setEnabled(True))
        self._lookup.start()

    def _on_found(self, result):
        self.lookup_done = True
        self._nome = result.get("nome", "")
        self._loja = result.get("loja", "")
        self._preco = result.get("preco")
        price_text = format_price(self._preco) if self._preco is not None else "não encontrado"
        self.result_label.setText(f"{self._nome} — {self._loja} — preço: {price_text}")
        self.lookup_status.setText("Produto encontrado.")
        if self._preco is not None and not self.target_edit.text().strip():
            self.target_edit.setText(str(self._preco).replace(".", ","))

    def _on_failed(self, error):
        self.lookup_done = True
        self.lookup_status.setText("Não foi possível buscar o produto (página bloqueada ou erro).")
        self.result_label.setText(str(error)[:140])
        self._nome = ""
        self._loja = ""
        self._preco = None

    def _on_accept(self):
        url = self.url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "Compras", "Informe a URL do produto.")
            return
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        alvo = scraper_compras.normalize_price(self.target_edit.text())
        self._result = {
            "url": url,
            "alvo": alvo or 0.0,
            "nome": self._nome or url,
            "loja": self._loja,
            "preco": self._preco,
        }
        self.accept()

    def result_data(self):
        return getattr(self, "_result", None)


class TargetDialog(QDialog):
    def __init__(self, product, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editar preço alvo")
        self.setMinimumWidth(380)
        self._result = None

        form = QFormLayout(self)
        name = QLabel(product.nome)
        name.setObjectName("prodMeta")
        name.setWordWrap(True)
        form.addRow("Produto:", name)
        self.target_edit = QLineEdit()
        self.target_edit.setText(format_price(product.preco_alvo) if product.preco_alvo else "")
        self.target_edit.setPlaceholderText("ex.: 150,00 (vazio = sem alvo)")
        self.target_edit.selectAll()
        form.addRow("Preço alvo:", self.target_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _on_accept(self):
        text = self.target_edit.text().strip()
        if not text:
            self._result = 0.0
            self.accept()
            return
        alvo = scraper_compras.normalize_price(text)
        if alvo is None:
            QMessageBox.warning(self, "Compras", "Informe um valor de preço alvo válido (ex.: 150,00).")
            return
        self._result = alvo
        self.accept()

    def result_value(self):
        return self._result


class ProductCard(QFrame):
    open_requested = Signal(str)
    delete_requested = Signal(str)
    target_edit_requested = Signal(str)

    def __init__(self, product, parent=None):
        super().__init__(parent)
        self.product = product
        self.setObjectName("prodCard")
        hit = compras.drop_hit(product)
        if hit:
            self.setProperty("hit", True)
        self.style().unpolish(self)
        self.style().polish(self)
        common.make_shadow(self, y=3, blur=16)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 12, 8)
        layout.setSpacing(10)

        icon = QLabel()
        icon.setObjectName("prodIcon")
        icon.setPixmap(qta.icon("fa5s.shopping-bag", color=theme.ACCENT).pixmap(22, 22))
        layout.addWidget(icon)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        self.title = QLabel(product.nome)
        self.title.setObjectName("prodTitle")
        self.title.setWordWrap(True)
        self.title.setToolTip(product.nome)
        text_col.addWidget(self.title)

        meta = QHBoxLayout()
        meta.setSpacing(8)
        if product.loja:
            badge = QLabel(product.loja)
            badge.setObjectName("newsSource")
            meta.addWidget(badge)
        target_label = QLabel(
            "Alvo: " + format_price(product.preco_alvo) if product.preco_alvo else "Sem preço alvo"
        )
        target_label.setObjectName("prodMeta")
        meta.addWidget(target_label)
        if hit:
            hit_badge = QLabel("Alvo atingido")
            hit_badge.setObjectName("prodHit")
            meta.addWidget(hit_badge)
        last = format_datetime(product.historico[-1]["data"]) if product.historico else ""
        if last:
            last_label = QLabel("· " + last)
            last_label.setObjectName("prodMeta")
            meta.addWidget(last_label)
        meta.addStretch()
        text_col.addLayout(meta)
        layout.addLayout(text_col, 1)

        self.price = QLabel(format_price(product.preco_atual))
        self.price.setObjectName("prodPrice")
        if product.preco_atual is None:
            self.price.setProperty("missing", True)
        elif hit:
            self.price.setProperty("hit", True)
        self.price.style().unpolish(self.price)
        self.price.style().polish(self.price)
        self.price.setMinimumWidth(110)
        self.price.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.price.setToolTip(self._history_tooltip())
        layout.addWidget(self.price)

        actions = QWidget()
        actions.setObjectName("prodActions")
        action_layout = QHBoxLayout(actions)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(2)
        open_btn = QToolButton()
        open_btn.setObjectName("cardBtn")
        open_btn.setIcon(qta.icon("fa5s.external-link-alt", color=theme.ACCENT))
        open_btn.setIconSize(QSize(14, 14))
        open_btn.setFixedSize(24, 24)
        open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        open_btn.setToolTip("Abrir na loja")
        open_btn.clicked.connect(lambda: self.open_requested.emit(product.url))
        target_btn = QToolButton()
        target_btn.setObjectName("cardBtn")
        target_btn.setIcon(qta.icon("fa5s.edit", color=theme.ACCENT))
        target_btn.setIconSize(QSize(14, 14))
        target_btn.setFixedSize(24, 24)
        target_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        target_btn.setToolTip("Editar preço alvo")
        target_btn.clicked.connect(lambda: self.target_edit_requested.emit(product.id))
        delete_btn = QToolButton()
        delete_btn.setObjectName("cardBtn")
        delete_btn.setIcon(qta.icon("fa5s.trash-alt", color=theme.DANGER))
        delete_btn.setIconSize(QSize(14, 14))
        delete_btn.setFixedSize(24, 24)
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.setToolTip("Remover")
        delete_btn.clicked.connect(lambda: self.delete_requested.emit(product.id))
        action_layout.addWidget(open_btn)
        action_layout.addWidget(target_btn)
        action_layout.addWidget(delete_btn)
        actions.setVisible(False)
        layout.addWidget(actions)
        self.actions_widget = actions

    def _history_tooltip(self):
        if not self.product.historico:
            return "Sem histórico de preços ainda"
        lines = [f"{format_datetime(h['data'])} · {format_price(h['preco'])}"
                 for h in self.product.historico[-8:]]
        return "\n".join(lines)

    def enterEvent(self, event):
        self.actions_widget.setVisible(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.rect().contains(self.mapFromGlobal(QCursor.pos())):
            self.actions_widget.setVisible(False)
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.open_requested.emit(self.product.url)
        super().mouseReleaseEvent(event)


class ComprasView(QWidget):
    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self._search = ""
        self._worker = None
        self._lookup_workers = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(10)
        title = common.make_title("fa5s.shopping-cart", "Compras")
        self.status = QLabel("")
        self.status.setObjectName("status")
        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("newsSearch")
        self.search_edit.setPlaceholderText("Buscar produtos…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setFixedWidth(200)
        self.search_edit.textChanged.connect(self._on_search)
        self.refresh_btn = QPushButton(" Atualizar preços")
        self.refresh_btn.setObjectName("refreshBtn")
        self.refresh_btn.setIcon(qta.icon("fa5s.sync-alt", color="#ffffff"))
        self.refresh_btn.setIconSize(QSize(15, 15))
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self._refresh_prices)
        self.search_btn = QPushButton(" Buscar produto")
        self.search_btn.setObjectName("secondaryBtn")
        self.search_btn.setIcon(qta.icon("fa5s.search", color=theme.ACCENT))
        self.search_btn.setIconSize(QSize(15, 15))
        self.search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.search_btn.setToolTip("Pesquisar um produto pelo nome nas lojas")
        self.search_btn.clicked.connect(self._search_products)
        self.add_btn = QPushButton(" Adicionar produto")
        self.add_btn.setObjectName("refreshBtn")
        self.add_btn.setIcon(qta.icon("fa5s.plus", color="#ffffff"))
        self.add_btn.setIconSize(QSize(15, 15))
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self._add_product)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.status)
        header.addWidget(self.search_edit)
        header.addWidget(self.refresh_btn)
        header.addWidget(self.search_btn)
        header.addWidget(self.add_btn)
        root.addLayout(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setObjectName("scrollArea")
        self.list_host = QWidget()
        self.list_layout = QVBoxLayout(self.list_host)
        self.list_layout.setContentsMargins(6, 0, 6, 6)
        self.list_layout.setSpacing(10)
        self.list_layout.addStretch()
        self.scroll.setWidget(self.list_host)
        root.addWidget(self.scroll, 1)

        self.refresh()

    def _on_search(self, text):
        self._search = text.strip().lower()
        self.refresh()

    def refresh(self):
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        products = self.manager.products
        if self._search:
            products = [p for p in products
                        if self._search in (p.nome + " " + p.loja).lower()]

        for product in products:
            card = ProductCard(product)
            card.open_requested.connect(self._open_link)
            card.delete_requested.connect(self._remove)
            card.target_edit_requested.connect(self._edit_target)
            self.list_layout.insertWidget(self.list_layout.count() - 1, card)

        total = len(self.manager.products)
        if not total:
            empty = QLabel("Nenhum produto acompanhado ainda.\n"
                           "Clique em \"+ Adicionar produto\" e cole a URL da loja.")
            empty.setObjectName("emptyLabel")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.list_layout.insertWidget(0, empty)
            self.status.setText("")
        elif not products:
            empty = QLabel("Nenhum produto encontrado para a busca.")
            empty.setObjectName("errorLabel")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.list_layout.insertWidget(0, empty)
            self.status.setText(f"{total} produtos · filtro")
        else:
            hits = sum(1 for p in self.manager.products if compras.drop_hit(p))
            text = f"{len(products)} produto{'s' if len(products) != 1 else ''}"
            if hits:
                text += f" · {hits} no alvo"
            self.status.setText(text)

    def _add_product(self):
        dialog = AddProductDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.result_data()
            product = self.manager.add(
                data["url"],
                nome=data["nome"],
                preco_alvo=data["alvo"],
                loja=data["loja"],
                preco_atual=data["preco"],
            )
            self.refresh()
            if data["preco"] is None and not dialog.lookup_done:
                self._start_lookup(product.id)

    def _search_products(self):
        dialog = SearchProductsDialog(self._add_result, self)
        dialog.exec()

    def _add_result(self, result):
        """Adiciona um resultado da busca na web ao acompanhamento. True se adicionado."""
        url = (result.get("url") or "").strip()
        if not url:
            return False
        for p in self.manager.products:
            if p.url.rstrip("/").lower() == url.rstrip("/").lower():
                return False
        self.manager.add(
            url,
            nome=result.get("nome") or url,
            loja=result.get("loja") or "",
            preco_alvo=0.0,
            preco_atual=result.get("preco"),
        )
        self.status.setText(f"\"{(result.get('nome') or url)[:40]}\" adicionado.")
        self.refresh()
        return True

    def _start_lookup(self, product_id):
        product = self.manager.get(product_id)
        if product is None:
            return
        worker = LookupWorker(product.url)
        worker.found.connect(lambda result, pid=product_id: self._on_lookup_found(pid, result))
        worker.failed.connect(lambda err, pid=product_id: self._on_lookup_failed(pid, err))
        worker.finished.connect(lambda w=worker: self._discard_lookup(w))
        self._lookup_workers.append(worker)
        self.status.setText("Buscando dados do produto…")
        worker.start()

    def _discard_lookup(self, worker):
        if worker in self._lookup_workers:
            self._lookup_workers.remove(worker)

    def _on_lookup_found(self, product_id, result):
        product = self.manager.get(product_id)
        if product is not None:
            if result.get("nome"):
                product.nome = result["nome"]
            if result.get("loja"):
                product.loja = result["loja"]
            if result.get("preco") is not None:
                self.manager.update_price(product_id, result["preco"])
            else:
                self.manager.save()
        self.refresh()

    def _on_lookup_failed(self, product_id, error):
        self.refresh()

    def _refresh_prices(self):
        if self._worker is not None and self._worker.isRunning():
            return
        if not self.manager.products:
            self.status.setText("Nenhum produto para atualizar.")
            return
        self.refresh_btn.setEnabled(False)
        self.status.setText("Atualizando preços…")
        self._worker = PriceWorker(self.manager, self)
        self._worker.finished.connect(self._on_prices_done)
        self._worker.start()

    def _on_prices_done(self, ok, fail):
        self.refresh_btn.setEnabled(True)
        self._worker = None
        self.refresh()
        if fail:
            msg = f"{ok} atualizados · {fail} falha{'s' if fail != 1 else ''}"
            self.status.setText(msg + " — lojas com anti-bot podem não responder.")
        else:
            self.status.setText(f"{ok} atualizado{'s' if ok != 1 else ''}")

    def _edit_target(self, product_id):
        product = self.manager.get(product_id)
        if product is None:
            return
        dialog = TargetDialog(product, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.manager.set_target(product_id, dialog.result_value())
            self.refresh()

    def _open_link(self, url):
        QDesktopServices.openUrl(QUrl(url))

    def _remove(self, product_id):
        product = self.manager.get(product_id)
        if product is None:
            return
        answer = QMessageBox.question(
            self,
            "Remover produto",
            f"Deixar de acompanhar \"{product.nome}\"?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.manager.remove(product_id)
            self.refresh()

    def shutdown(self):
        if self._worker is not None:
            self._worker.requestInterruption()
            self._worker.wait(3000)
        for worker in self._lookup_workers:
            worker.requestInterruption()
            worker.wait(2000)
