"""Testes para notes.py (gerenciamento de notas e markdown, sem UI)."""

import pytest

import notes
from notes import NoteManager


def test_notemanager_roundtrip(tmp_path):
    path = tmp_path / "notas.json"
    mgr = NoteManager(path)
    n = mgr.add("Título", content="Corpo", priority="alta", category="Pessoal")
    assert len(mgr.notes) == 1

    mgr2 = NoteManager(path)
    assert len(mgr2.notes) == 1
    loaded = mgr2.notes[0]
    assert loaded.title == "Título"
    assert loaded.content == "Corpo"
    assert loaded.priority == "alta"
    assert loaded.category == "Pessoal"


def test_notemanager_update_remove(tmp_path):
    mgr = NoteManager(tmp_path / "n.json")
    a = mgr.add("a", content="x")
    b = mgr.add("b")
    mgr.remove(a.id)
    assert [x.id for x in mgr.notes] == [b.id]


def test_notemanager_toggle_pin(tmp_path):
    mgr = NoteManager(tmp_path / "n.json")
    a = mgr.add("a")
    assert mgr.toggle_pin(a.id).pinned is True
    assert mgr.toggle_pin("inexistente") is None


def test_notemanager_sorted_notes_pin_first(tmp_path):
    mgr = NoteManager(tmp_path / "n.json")
    low = mgr.add("sem prioridade")
    high = mgr.add("prioridade alta", priority="alta")
    pinned = mgr.add("fixado (mais velho)", priority="baixa")
    mgr.toggle_pin(pinned.id)
    ordered = [n.id for n in mgr.sorted_notes()]
    # fixado vem primeiro; depois prioridade alta antes da baixa/sem prioridade
    assert ordered[0] == pinned.id
    assert ordered.index(high.id) < ordered.index(low.id)


def test_notemanager_search(tmp_path):
    mgr = NoteManager(tmp_path / "n.json")
    mgr.add("Compras", content="arroz e feijão")
    mgr.add("Estudo", content="python")
    assert len(mgr.search("arroz")) == 1
    assert len(mgr.search("python")) == 1
    assert len(mgr.search("nada")) == 0
    assert mgr.search("")[0].title in ("Compras", "Estudo")


def test_notemanager_attach_detach(tmp_path, monkeypatch):
    source = tmp_path / "arq.png"
    source.write_bytes(b"\x89PNG\r\n")
    attach_dir = tmp_path / "anexos"
    monkeypatch.setattr(notes, "DEFAULT_ATTACH_DIR", str(attach_dir))
    monkeypatch.setattr(notes, "_DIR", str(tmp_path))

    mgr = NoteManager(tmp_path / "n.json")
    n = mgr.add("com anexo")
    att = mgr.attach(n.id, str(source))
    assert att is not None
    assert att["name"] == "arq.png"
    assert len(mgr.notes[0].attachments) == 1

    # roundtrip após salvar
    mgr2 = NoteManager(tmp_path / "n.json")
    assert len(mgr2.notes[0].attachments) == 1

    assert mgr.detach(n.id, att["id"]) is True
    assert len(mgr.notes[0].attachments) == 0
    assert mgr.detach(n.id, att["id"]) is False


def test_attach_missing_source(tmp_path):
    mgr = NoteManager(tmp_path / "n.json")
    n = mgr.add("x")
    assert mgr.attach(n.id, str(tmp_path / "nao_existe.bin")) is None


def test_attachment_path_abs_and_relative():
    assert notes.NoteManager.attachment_path(None, {"path": "C:/abs.png"}) == "C:/abs.png"
    joined = notes.NoteManager.attachment_path(None, {"path": "anexos/x.png"})
    assert joined is not None and joined.replace("\\", "/").endswith("anexos/x.png")
    assert notes.NoteManager.attachment_path(None, {"path": ""}) is None


def test_markdown_to_html():
    html = notes.markdown_to_html("# Título\n\ntexto com **negrito**")
    assert "<h1>Título</h1>" in html
    assert "<b>negrito</b>" in html
    assert "<p>texto com " in html


def test_markdown_to_html_lists_and_tasks():
    html = notes.markdown_to_html("- [x] feito\n- [ ] pendente")
    assert "<ul>" in html
    assert "&#9745;" in html
    assert "&#9744;" in html


def test_markdown_to_html_code_block():
    html = notes.markdown_to_html("```\nprint('oi')\n```")
    assert "<pre>" in html


def test_markdown_to_html_escape():
    html = notes.markdown_to_html("<script>alert(1)</script>")
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_preview_html_contains_style():
    html = notes.preview_html("ola")
    assert "<html>" in html
    assert "font-size" in html
    assert "ola" in html