"""Pruebas de los modelos financieros.

Verifican las validaciones y restricciones básicas de cuotas y movimientos.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensiones import db
from app.models import Cuota, Movimiento


def test_cuota_usa_estado_pendiente_y_acepta_datos_validos(app, crear_usuario):
    usuario = crear_usuario(email="socia@example.com")
    cuota = Cuota(
        usuario=usuario,
        periodo=2026,
        importe=Decimal("25.50"),
        numero_recibo="R-2026-0001",
    )
    db.session.add(cuota)
    db.session.commit()

    assert cuota.estado == "pendiente"
    assert cuota.importe == Decimal("25.50")
    assert cuota.fecha_pago is None


def test_cuota_rechaza_estado_y_numero_recibo_invalidos():
    with pytest.raises(ValueError, match="Estado de cuota no permitido"):
        Cuota(estado="vencida")

    with pytest.raises(ValueError, match="formato R-AAAA-NNNN"):
        Cuota(numero_recibo="recibo-1")


@pytest.mark.parametrize(
    "importe",
    [Decimal("0"), Decimal("-1.00"), Decimal("NaN"), Decimal("Infinity")],
)
@pytest.mark.parametrize("modelo", [Cuota, Movimiento])
def test_modelos_rechazan_importes_no_positivos(modelo, importe):
    with pytest.raises(ValueError, match="mayor que cero"):
        modelo(importe=importe)


def test_modelos_financieros_rechazan_importe_float():
    with pytest.raises(TypeError, match="valor Decimal"):
        Cuota(importe=25.50)

    with pytest.raises(TypeError, match="valor Decimal"):
        Movimiento(importe=25.50)


def test_cuota_no_permite_mas_de_una_por_socio_y_periodo(app, crear_usuario):
    usuario = crear_usuario(email="socia@example.com")
    db.session.add(
        Cuota(
            usuario=usuario,
            periodo=2026,
            importe=Decimal("25.00"),
        )
    )
    db.session.commit()

    db.session.add(
        Cuota(
            usuario=usuario,
            periodo=2026,
            importe=Decimal("30.00"),
        )
    )
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_movimiento_acepta_tipo_valido_y_categoria_opcional(app):
    movimiento = Movimiento(
        tipo="ingreso",
        concepto="Cuota anual",
        importe=Decimal("25.00"),
        fecha=date(2026, 1, 1),
    )
    db.session.add(movimiento)
    db.session.commit()

    assert movimiento.tipo == "ingreso"
    assert movimiento.categoria is None


@pytest.mark.parametrize("tipo", ["transferencia", ""])
def test_movimiento_rechaza_tipo_no_permitido(tipo):
    with pytest.raises(ValueError, match="Tipo de movimiento no permitido"):
        Movimiento(tipo=tipo)


def test_tablas_financieras_quedan_registradas_en_la_factory(app):
    assert "cuota" in db.metadata.tables
    assert "movimiento" in db.metadata.tables
    assert "finanzas" in app.blueprints
