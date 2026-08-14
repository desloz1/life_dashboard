"""Diálogos e linhas de resultado da aba Compras (busca web, adicionar, alvo)."""

import qtawesome as qta
from PySide6.QtCore import QSize, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
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
import scraper_compras
import theme
from compras_util import format_price
from compras_workers import LookupWorker, SearchWorker


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