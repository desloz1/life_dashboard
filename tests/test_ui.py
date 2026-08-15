"""Testes de UI simples com pytest-qt (render offscreen, sem rede).

Cobrem widgets centrais da interface para pegar regressões de construção/estilo
sem depender de rede ou workers. Obtêm QApplication via `qtbot` do pytest-qt.
"""

import datetime
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

import compras
import stylesheet
import theme
import theme_palette
from compras_ui import ProductCard
from dashboard_widgets import DashTodayBox, SummaryCard, TaskWeekChart
from PySide6.QtWidgets import QApplication, QLabel


@pytest.fixture()
def app(qapp):
    theme.apply_theme(qapp, "dark")
    yield qapp


def test_theme_builds_qss_for_both(app):
    theme.apply_theme(app, "dark")
    assert theme.CURRENT_THEME == "dark"
    qss = stylesheet.build_stylesheet(theme_palette.THEMES["dark"])
    assert "#dashToday" in qss
    assert "#prodChart" in qss
    theme.apply_theme(app, "light")
    assert theme.CURRENT_THEME == "light"
    assert theme.ACCENT == "#1a73e8"


@pytest.mark.parametrize("name", ["dark", "light"])
def test_summary_card_render(app, name):
    theme.apply_theme(app, name)
    card = SummaryCard("fa5s.bell", theme.ACCENT, "Lembretes")
    app.allWidgets()  # força estilo
    card.value.setText("3 atrasado")
    card.show()
    assert card.value.text() == "3 atrasado"
    assert card.objectName() == "dashCard"
    card.deleteLater()


@pytest.mark.parametrize("name", ["dark", "light"])
def test_task_chart_paint(app, name):
    theme.apply_theme(app, name)
    chart = TaskWeekChart()
    chart.set_data([(datetime.date.today() - datetime.timedelta(days=i), 1 if i % 2 else 0)
                    for i in range(7)])
    chart.resize(600, 120)
    chart.show()
    app.processEvents()
    assert chart.width() == 600
    chart.deleteLater()


def test_task_chart_empty(app):
    chart = TaskWeekChart()
    chart.set_data([])
    chart.resize(300, 120)
    chart.show()
    app.processEvents()
    chart.deleteLater()


def test_product_card(app):
    product = compras.Product(
        id="1",
        nome="Teste",
        url="http://exemplo.com",
        loja="Kabum",
        preco_atual=100.0,
        preco_alvo=90.0,
        historico=[
            {"data": "2026-08-10T10:00:00", "preco": 120.0},
            {"data": "2026-08-12T10:00:00", "preco": 110.0},
            {"data": "2026-08-15T10:00:00", "preco": 100.0},
        ],
    )
    card = ProductCard(product)
    card.show()
    assert "100,00" in card.price.text()
    labels = [w.text() for w in card.findChildren(QLabel)]
    assert any("Alvo" in text for text in labels)
    assert "R$" in card.price.toolTip() and "120,00" in card.price.toolTip()
    assert card.chart.isHidden()
    card._toggle_chart()
    assert not card.chart.isHidden()
    card.chart.show()
    card.chart.resize(400, 92)
    app.processEvents()
    card.deleteLater()


def test_product_card_no_history(app):
    product = compras.Product(id="2", nome="Só nome", url="http://exemplo.com")
    card = ProductCard(product)
    card.chart.show()
    card.chart.resize(300, 92)
    app.processEvents()
    card.deleteLater()


def test_dash_today_box(app):
    box = DashTodayBox()
    box.set_items(3, 1, holiday="Independência", n_cameras=2)
    assert "3 tarefas para hoje" in box.tasks_label.text()
    assert "1 lembrete hoje" in box.reminders_label.text()
    assert "Independência" in box.holiday_label.text()
    assert "2" in box.cameras_label.text()
    box.set_items(0, 0, holiday=None, n_cameras=0)
    assert box.holiday_label.isHidden()
    box.set_weather("fa5s.sun", "#f9c74f", 18, "Céu limpo", 24, 12)
    assert box.weather_temp.text() == "18°C"
    box.show()
    app.processEvents()
    box.deleteLater()