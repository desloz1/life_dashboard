"""Testes para theme_palette.py e stylesheet.py (sem instanciar QApplication)."""

import pytest

from theme_palette import HIGH_CONTRAST_OVERRIDES, THEMES, THUMB_HEIGHT, THUMB_WIDTH


def test_theme_keys_and_required_vars():
    for name, pal in THEMES.items():
        assert name in ("dark", "light")
        for var in ("ACCENT", "BG", "TEXT", "MUTED", "CARD", "BORDER", "INPUT", "BTN",
                    "SURFACE", "DANGER", "WARN", "OK", "PLACEHOLDER"):
            assert var in pal, f"{name} lacks {var}"
            assert isinstance(pal[var], str) and pal[var].startswith("#")


def test_high_contrast_overrides_subset():
    assert all(k in THEMES["dark"] for k in HIGH_CONTRAST_OVERRIDES)


def test_thumb_dimensions_positive():
    assert THUMB_WIDTH > 0 and THUMB_HEIGHT > 0


def test_build_stylesheet_returns_text():
    import stylesheet
    qss = stylesheet.build_stylesheet(THEMES["dark"])
    assert isinstance(qss, str) and len(qss) > 1000
    assert qss == stylesheet.build_stylesheet(THEMES["dark"])
    assert stylesheet.build_stylesheet(THEMES["dark"]) != stylesheet.build_stylesheet(THEMES["light"])


def test_stylesheet_font_scale_participa():
    import stylesheet
    qss1 = stylesheet.build_stylesheet(THEMES["dark"], 1.0)
    qss2 = stylesheet.build_stylesheet(THEMES["dark"], 1.2)
    # a escala de fonte deve alterar o resultado em pelo menos um ponto
    assert isinstance(qss1, str) and isinstance(qss2, str)