import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime

import log

logger = log.get_logger("life_dashboard.compras")

_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PATH = os.path.join(_DIR, "compras.json")


def _now():
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class Product:
    id: str
    nome: str
    url: str
    loja: str = ""
    preco_atual: float = None  # None quando ainda não coletado
    preco_alvo: float = 0.0
    drop_notified: str = ""  # ISO date do último alerta de queda
    historico: list = field(default_factory=list)  # [{"data": ISO datetime, "preco": float}]


def drop_hit(product):
    """Preço atual atingiu/abaixou do preço alvo."""
    if product.preco_atual is None or not product.preco_alvo:
        return False
    return product.preco_atual <= product.preco_alvo


def last_price(product):
    """Último preço registrado no histórico (ou preco_atual)."""
    if product.historico:
        return product.historico[-1].get("preco")
    return product.preco_atual


class PriceTracker:
    def __init__(self, path=DEFAULT_PATH):
        self.path = path
        self.products = []
        self.load()

    def load(self):
        self.products = []
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            for item in data or []:
                if not isinstance(item, dict) or not item.get("id"):
                    continue
                historico = item.get("historico") or []
                if not isinstance(historico, list):
                    historico = []
                historico = [
                    {"data": str(h.get("data", "")), "preco": self._price(h.get("preco"))}
                    for h in historico
                    if isinstance(h, dict) and h.get("data")
                ]
                preco_atual = self._price(item.get("preco_atual"))
                self.products.append(Product(
                    id=item["id"],
                    nome=item.get("nome", "Produto"),
                    url=item.get("url", ""),
                    loja=item.get("loja", ""),
                    preco_atual=preco_atual,
                    preco_alvo=self._price(item.get("preco_alvo")) or 0.0,
                    drop_notified=item.get("drop_notified", ""),
                    historico=historico,
                ))
        except (OSError, ValueError) as exc:
            logger.error("Falha ao carregar produtos de %s: %s", self.path, exc)
            return

    @staticmethod
    def _price(value):
        try:
            return round(float(value), 2)
        except (TypeError, ValueError):
            return None

    def save(self):
        data = []
        for p in self.products:
            data.append({
                "id": p.id,
                "nome": p.nome,
                "url": p.url,
                "loja": p.loja,
                "preco_atual": p.preco_atual,
                "preco_alvo": p.preco_alvo,
                "drop_notified": p.drop_notified,
                "historico": p.historico,
            })
        try:
            with open(self.path, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(data, ensure_ascii=False, indent=2))
        except OSError as exc:
            logger.error("Falha ao salvar produtos em %s: %s", self.path, exc)

    def add(self, url, nome="", preco_alvo=0.0, loja="", preco_atual=None):
        product = Product(
            id=uuid.uuid4().hex,
            nome=nome or url,
            url=url,
            loja=loja,
            preco_atual=preco_atual,
            preco_alvo=self._price(preco_alvo) or 0.0,
        )
        if preco_atual is not None:
            product.historico.append({"data": _now(), "preco": product.preco_atual})
        self.products.append(product)
        self.save()
        return product

    def remove(self, product_id):
        self.products = [p for p in self.products if p.id != product_id]
        self.save()

    def get(self, product_id):
        return next((p for p in self.products if p.id == product_id), None)

    def update_price(self, product_id, preco):
        """Registra uma nova coleta de preço (não sobrescreve quando a coleta falha)."""
        product = self.get(product_id)
        if product is None:
            return None
        price = self._price(preco)
        if price is not None:
            product.preco_atual = price
            product.historico.append({"data": _now(), "preco": price})
            product.drop_notified = ""  # permite novo alerta se o preço subir e cair de novo
            self.save()
        return product

    def set_target(self, product_id, preco_alvo):
        product = self.get(product_id)
        if product is None:
            return False
        product.preco_alvo = self._price(preco_alvo) or 0.0
        self.save()
        return True

    def hit_products(self):
        """Produtos cujo preço atual atingiu/abaixou do alvo."""
        return [p for p in self.products if drop_hit(p)]

    def mark_drop_notified(self, product_ids, day=None):
        day = day or date.today().isoformat()
        changed = False
        for p in self.products:
            if p.id in product_ids and p.drop_notified != day:
                p.drop_notified = day
                changed = True
        if changed:
            self.save()
