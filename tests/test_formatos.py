"""Pruebas de los filtros Jinja para presentar importes, fechas y horas."""

from datetime import date, datetime
from decimal import Decimal


def test_filtro_euros_formatea_miles_y_decimales(app):
    formato = app.jinja_env.filters["euros"]

    assert formato(Decimal("1234.56")) == "1.234,56 €"
    assert formato(Decimal("0.5")) == "0,50 €"


def test_filtro_fecha_es_distingue_fecha_y_fecha_con_hora(app):
    formato = app.jinja_env.filters["fecha_es"]

    assert formato(date(2026, 10, 23)) == "23/10/2026"
    assert formato(datetime(2026, 10, 23, 9, 5)) == "23/10/2026 09:05"
