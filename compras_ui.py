"""View da aba Compras + card de produto (fachada da UI).

- Diálogos e linhas de resultado → `compras_dialogs.py`
- Workers (QThread) → `compras_workers.py`
- Formatação → `compras_util.py`
- Dados → `compras.py`

`ComprasView`, `ProductCard`, `format_price` e `format_datetime` permanecem
acessíveis daqui (compatível com `from compras_ui import ComprasView, format_price`).
"""

import qtawesome as qta
from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QUrl, Signal
from PySide6.QtGui import QColor, QCursor, QDesktopServices, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (
    QDialog,
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
import theme
from compras_dialogs import AddProductDialog, SearchProductsDialog, TargetDialog
from compras_util import format_datetime, format_price
from compras_workers import LookupWorker, PriceWorker


class PriceChart(QWidget):
    """Mini-gráfico com a evolução do preço do produto (últimas coletas)."""

    def __init__(self, product, parent=None):
        super().__init__(parent)
        self.product = product
        self.setObjectName("prodChart")
        self.setFixedHeight(92)
        self.setMinimumWidth(220)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        history = [
            {"data": h.get("data", ""), "preco": float(h["preco"])}
            for h in self.product.historico
            if h.get("preco") is not None
        ]
        if not history:
            painter.setPen(QColor(theme.MUTED))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Sem histórico de preços")
            return
        if len(history) == 1:
            painter.setPen(QColor(theme.MUTED))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                             "Preço atual: " + format_price(history[0]["preco"]))
            return

        history = history[-20:]
        prices = [h["preco"] for h in history]
        lo, hi = min(prices), max(prices)
        span = (hi - lo) or 1.0
        margin = 8
        margin_top, margin_bottom = 16, 18
        chart_w = self.width() - margin * 2
        chart_h = self.height() - margin_top - margin_bottom
        baseline = self.height() - margin_bottom

        def y_for(value):
            return margin_top + (hi - value) / span * chart_h

        step = chart_w / (len(prices) - 1)
        points = [QPointF(margin + i * step, y_for(p)) for i, p in enumerate(prices)]

        font = painter.font()
        font.setPointSizeF(max(7, 8 * theme.FONT_SCALE))
        painter.setFont(font)

        painter.setPen(QColor(theme.BORDER))
        painter.drawLine(margin, baseline, self.width() - margin, baseline)

        painter.setPen(QColor(theme.MUTED))
        painter.drawText(QRectF(margin, margin_top - 14, 100, 12),
                         Qt.AlignmentFlag.AlignLeft, "mín " + format_price(lo))
        painter.drawText(QRectF(self.width() - margin - 100, margin_top - 14, 100, 12),
                         Qt.AlignmentFlag.AlignRight, "máx " + format_price(hi))
        first_date = format_datetime(history[0]["data"])[:5]
        last_date = format_datetime(history[-1]["data"])[:5]
        painter.drawText(QRectF(margin, baseline + 2, 100, 12),
                         Qt.AlignmentFlag.AlignLeft, "→ " + first_date)
        painter.drawText(QRectF(self.width() - margin - 100, baseline + 2, 100, 12),
                         Qt.AlignmentFlag.AlignRight, last_date)

        painter.setPen(QPen(QColor(theme.ACCENT), 2))
        painter.drawPolyline(QPolygonF(points))
        painter.setBrush(QColor(theme.ACCENT))
        painter.setPen(Qt.PenStyle.NoPen)
        for pt in points:
            painter.drawEllipse(pt, 2.5, 2.5)

        painter.setPen(QColor(theme.TEXT))
        painter.drawText(QRectF(points[-1].x() - 55, max(0.0, points[-1].y() - 18), 115, 14),
                         Qt.AlignmentFlag.AlignHCenter, format_price(prices[-1]))
        painter.end()


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

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        row = QWidget()
        row.setObjectName("prodCardRow")
        layout = QHBoxLayout(row)
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
        chart_btn = QToolButton()
        chart_btn.setObjectName("cardBtn")
        chart_btn.setIcon(qta.icon("fa5s.chart-line", color=theme.ACCENT))
        chart_btn.setIconSize(QSize(14, 14))
        chart_btn.setFixedSize(24, 24)
        chart_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        chart_btn.setToolTip("Evolução do preço")
        chart_btn.clicked.connect(self._toggle_chart)
        action_layout.addWidget(open_btn)
        action_layout.addWidget(target_btn)
        action_layout.addWidget(delete_btn)
        action_layout.addWidget(chart_btn)
        actions.setVisible(False)
        layout.addWidget(actions)
        self.actions_widget = actions

        outer.addWidget(row)
        self.chart = PriceChart(product)
        self.chart.setVisible(False)
        outer.addWidget(self.chart)

    def _toggle_chart(self):
        if not hasattr(self, "chart"):
            return
        self.chart.setVisible(self.chart.isHidden())

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