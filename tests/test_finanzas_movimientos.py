"""Pruebas del libro de ingresos y gastos.

Comprueban permisos, operaciones de movimientos y resumen anual.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.extensiones import db
from app.models import Cuota, Movimiento
from tests.conftest import iniciar_sesion


def crear_movimiento(**cambios):
    datos = {
        "tipo": "ingreso",
        "concepto": "Subvención cultural",
        "importe": Decimal("100.00"),
        "fecha": date(2026, 3, 15),
    }
    datos.update(cambios)
    movimiento = Movimiento(**datos)
    db.session.add(movimiento)
    db.session.commit()
    return movimiento


def crear_cuota(usuario, **cambios):
    datos = {
        "usuario": usuario,
        "periodo": 2026,
        "importe": Decimal("25.00"),
        "estado": "pagada",
        "fecha_pago": date(2026, 4, 10),
        "numero_recibo": "R-2026-0001",
    }
    datos.update(cambios)
    cuota = Cuota(**datos)
    db.session.add(cuota)
    db.session.commit()
    return cuota


def datos_movimiento(**cambios):
    datos = {
        "tipo": "ingreso",
        "concepto": "Actuación",
        "importe": "125.50",
        "fecha": "2026-05-20",
        "categoria": "Eventos",
    }
    datos.update(cambios)
    return datos


def test_socio_no_accede_a_gestion_de_movimientos(cliente, crear_usuario):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    movimiento = crear_movimiento()
    iniciar_sesion(cliente, socio)

    respuestas = [
        cliente.get("/finanzas/movimientos"),
        cliente.get("/finanzas/movimientos/nuevo"),
        cliente.post("/finanzas/movimientos/nuevo"),
        cliente.get(f"/finanzas/movimientos/{movimiento.id}/editar"),
        cliente.post(f"/finanzas/movimientos/{movimiento.id}/editar"),
        cliente.post(f"/finanzas/movimientos/{movimiento.id}/eliminar"),
    ]

    assert [respuesta.status_code for respuesta in respuestas] == [403] * 6


def test_resumen_suma_ingresos_cuotas_y_gastos_del_anio(
    cliente, crear_usuario
):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    crear_movimiento(
        importe=Decimal("100.25"),
        fecha=date(2026, 1, 2),
    )
    crear_movimiento(
        tipo="gasto",
        concepto="Alquiler",
        importe=Decimal("30.10"),
        fecha=date(2026, 2, 2),
    )
    crear_movimiento(
        tipo="gasto",
        concepto="Material",
        importe=Decimal("20.00"),
        fecha=date(2025, 12, 31),
    )
    socia = crear_usuario(email="socia@example.com", estado="activo")
    crear_cuota(socia, importe=Decimal("40.50"))
    crear_cuota(
        crear_usuario(email="anulada@example.com", estado="activo"),
        estado="anulada",
        fecha_pago=date(2026, 7, 1),
        numero_recibo="R-2026-0002",
    )
    crear_cuota(
        crear_usuario(email="otro-anio@example.com", estado="activo"),
        fecha_pago=date(2025, 12, 31),
        numero_recibo="R-2025-0001",
    )
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.get("/finanzas/movimientos?anio=2026")

    assert respuesta.status_code == 200
    assert "100,25 €".encode() in respuesta.data
    assert "40,50 €".encode() in respuesta.data
    assert "30,10 €".encode() in respuesta.data
    assert "110,65 €".encode() in respuesta.data
    assert b"Material" not in respuesta.data


def test_listado_filtra_por_concepto_tipo_y_anio(cliente, crear_usuario):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    crear_movimiento(concepto="Subvencion anual")
    crear_movimiento(
        tipo="gasto",
        concepto="Compra de vestuario",
        importe=Decimal("60.00"),
        fecha=date(2026, 8, 1),
    )
    crear_movimiento(
        concepto="Subvencion anterior",
        fecha=date(2025, 8, 1),
    )
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.get(
        "/finanzas/movimientos?q=subvencion&tipo=ingreso&anio=2026"
    )

    assert respuesta.status_code == 200
    assert b"Subvencion anual" in respuesta.data
    assert b"Compra de vestuario" not in respuesta.data
    assert b"Subvencion anterior" not in respuesta.data


def test_administrador_crea_edita_y_elimina_movimiento(
    cliente, crear_usuario
):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    iniciar_sesion(cliente, administrador)

    respuesta_crear = cliente.post(
        "/finanzas/movimientos/nuevo",
        data=datos_movimiento(),
        follow_redirects=True,
    )
    movimiento = db.session.scalar(
        db.select(Movimiento).where(Movimiento.concepto == "Actuación")
    )
    assert respuesta_crear.status_code == 200
    assert movimiento is not None
    assert movimiento.importe == Decimal("125.50")
    assert movimiento.categoria == "Eventos"

    respuesta_editar = cliente.post(
        f"/finanzas/movimientos/{movimiento.id}/editar",
        data=datos_movimiento(
            tipo="gasto",
            concepto="Actuación modificada",
            importe="150.25",
            categoria="",
        ),
        follow_redirects=True,
    )
    assert respuesta_editar.status_code == 200
    assert movimiento.tipo == "gasto"
    assert movimiento.concepto == "Actuación modificada"
    assert movimiento.importe == Decimal("150.25")
    assert movimiento.categoria is None

    respuesta_eliminar = cliente.post(
        f"/finanzas/movimientos/{movimiento.id}/eliminar"
    )
    assert respuesta_eliminar.status_code == 302
    assert db.session.get(Movimiento, movimiento.id) is None


@pytest.mark.parametrize(
    "cambios",
    [
        {"tipo": "transferencia"},
        {"concepto": ""},
        {"importe": "0"},
        {"importe": "-1"},
        {"importe": "texto"},
        {"importe": "NaN"},
        {"importe": "100000000.00"},
        {"fecha": ""},
    ],
)
def test_formulario_rechaza_movimientos_invalidos(
    cliente, crear_usuario, cambios
):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.post(
        "/finanzas/movimientos/nuevo",
        data=datos_movimiento(**cambios),
    )

    assert respuesta.status_code == 200
    assert db.session.scalar(db.select(Movimiento)) is None


def test_finanzas_aparece_en_navegacion_solo_para_administradores(
    cliente, crear_usuario
):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    iniciar_sesion(cliente, socio)
    respuesta_socio = cliente.get("/inicio")
    cliente.post("/auth/logout")

    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    iniciar_sesion(cliente, administrador)
    respuesta_admin = cliente.get("/inicio")

    assert b">Finanzas</a>" not in respuesta_socio.data
    assert b">Finanzas</a>" in respuesta_admin.data
