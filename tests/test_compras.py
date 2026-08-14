"""Testes para compras.py (PriceTracker e utilitários, sem UI)."""

import pytest

import compras
from compras import Product, PriceTracker, drop_hit, last_price


def test_drop_hit():
    prod = Product(id="1", nome="p", url="u", preco_atual=10.0, preco_alvo=12.0)
    assert drop_hit(prod) is True
    prod.preco_atual = 15.0
    assert drop_hit(prod) is False
    prod.preco_atual = None
    assert drop_hit(prod) is False
    prod.preco_atual = 5.0
    prod.preco_alvo = 0.0
    assert drop_hit(prod) is False


def test_last_price():
    prod = Product(id="1", nome="p", url="u", preco_atual=10.0)
    assert last_price(prod) == 10.0
    prod.historico = [{"data": "2026-01-01T00:00:00", "preco": 8.0},
                      {"data": "2026-01-02T00:00:00", "preco": 6.0}]
    assert last_price(prod) == 6.0


def test_pricetracker_roundtrip(tmp_path):
    path = tmp_path / "compras.json"
    tracker = PriceTracker(path)
    p = tracker.add("https://amazon.com.br/x", nome="Fone", preco_alvo=200.0,
                    preco_atual=250.0, loja="Amazon")
    assert len(tracker.products) == 1

    t2 = PriceTracker(path)
    assert len(t2.products) == 1
    loaded = t2.products[0]
    assert loaded.id == p.id
    assert loaded.nome == "Fone"
    assert loaded.preco_alvo == 200.0
    assert loaded.preco_atual == 250.0
    assert loaded.loja == "Amazon"
    assert len(loaded.historico) == 1  # preco_atual inicial entra no histórico


def test_pricetracker_load_missing(tmp_path):
    tracker = PriceTracker(tmp_path / "nao_existe.json")
    assert tracker.products == []


def test_pricetracker_remove_get(tmp_path):
    tracker = PriceTracker(tmp_path / "c.json")
    a = tracker.add("https://a.com", nome="A")
    b = tracker.add("https://b.com", nome="B")
    assert tracker.get(a.id).nome == "A"
    assert tracker.get("inexistente") is None
    tracker.remove(a.id)
    assert tracker.get(a.id) is None
    assert len(tracker.products) == 1


def test_pricetracker_update_price(tmp_path):
    tracker = PriceTracker(tmp_path / "c.json")
    p = tracker.add("https://a.com", nome="A", preco_alvo=100.0, preco_atual=150.0)
    tracker.update_price(p.id, 95.0)
    assert tracker.get(p.id).preco_atual == 95.0
    assert len(tracker.get(p.id).historico) == 2
    # atualização inválida não muda nada
    tracker.update_price(p.id, "abc")
    assert tracker.get(p.id).preco_atual == 95.0
    assert len(tracker.get(p.id).historico) == 2
    assert tracker.update_price("inexistente", 10.0) is None


def test_pricetracker_set_target(tmp_path):
    tracker = PriceTracker(tmp_path / "c.json")
    p = tracker.add("https://a.com")
    assert tracker.set_target(p.id, 99.99) is True
    assert tracker.get(p.id).preco_alvo == 99.99
    assert tracker.set_target("inexistente", 5.0) is False


def test_pricetracker_hit_and_mark(tmp_path):
    tracker = PriceTracker(tmp_path / "c.json")
    a = tracker.add("https://a.com", nome="A", preco_alvo=100.0, preco_atual=80.0)
    tracker.add("https://b.com", nome="B", preco_alvo=100.0, preco_atual=150.0)
    assert [p.nome for p in tracker.hit_products()] == ["A"]
    tracker.mark_drop_notified([a.id])
    assert tracker.get(a.id).drop_notified != ""


def test_pricetracker_preserves_bad_historic_rows(tmp_path):
    data = [
        {"id": "x1", "nome": "ok", "url": "u", "historico": [{"data": "2026-01-01", "preco": 10}],
         "preco_atual": 9, "preco_alvo": 10},
        {"id": "x2", "nome": "ruim", "url": "u", "historico": "nao-lista"},
        {"id": 123, "nome": "sem_id_string"},
        "linha-que-nao-e-dict",
    ]
    path = tmp_path / "c.json"
    path.write_text(__import__("json").dumps(data), encoding="utf-8")
    tracker = PriceTracker(path)
    names = {p.nome for p in tracker.products}
    assert "ok" in names
    assert "ruim" in names