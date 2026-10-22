"""Pruebas de la vista personal de cuotas y su integración en inicio.

Comprueban autenticación, aislamiento de datos y enlaces según el rol.
"""

from datetime import date
from decimal import Decimal

from flask import g

from app.extensiones import db
from app.models import Cuota


def iniciar_sesion(cliente, usuario):
    g.pop("_login_user", None)
    with cliente.session_transaction() as sesion:
        sesion["_user_id"] = str(usuario.id)
        sesion["_fresh"] = True


def crear_cuota(usuario, **cambios):
    datos = {
        "usuario": usuario,
        "periodo": 2026,
        "importe": Decimal("35.00"),
        "estado": "pendiente",
    }
    datos.update(cambios)
    cuota = Cuota(**datos)
    db.session.add(cuota)
    db.session.commit()
    return cuota


def test_mis_cuotas_muestra_solo_cuotas_propias_y_enlaza_recibo(
    cliente, crear_usuario
):
    socia = crear_usuario(email="socia@example.com", estado="activo")
    otra_socia = crear_usuario(email="otra@example.com", estado="activo")
    cuota_pagada = crear_cuota(
        socia,
        periodo=2026,
        estado="pagada",
        fecha_pago=date(2026, 5, 20),
        numero_recibo="R-2026-0001",
    )
    crear_cuota(otra_socia, periodo=2025)
    cuota_pendiente = crear_cuota(socia, periodo=2025)
    iniciar_sesion(cliente, socia)

    respuesta = cliente.get("/finanzas/mis-cuotas")

    assert respuesta.status_code == 200
    assert b"Mis cuotas" in respuesta.data
    assert b"R-2026-0001" in respuesta.data
    assert (
        f'href="/finanzas/cuotas/{cuota_pagada.id}/recibo"'.encode()
        in respuesta.data
    )
    assert (
        f'href="/finanzas/cuotas/{cuota_pendiente.id}/recibo"'.encode()
        not in respuesta.data
    )
    assert b"2025" in respuesta.data
    assert len(respuesta.data.split(b"2025")) == 2


def test_mis_cuotas_requiere_inicio_de_sesion(cliente):
    respuesta = cliente.get("/finanzas/mis-cuotas")

    assert respuesta.status_code == 302
    assert respuesta.headers["Location"].startswith("/auth/login?next=")


def test_navegacion_y_inicio_enlazan_mis_cuotas_para_socio(
    cliente, crear_usuario
):
    socia = crear_usuario(email="socia@example.com", estado="activo")
    iniciar_sesion(cliente, socia)

    respuesta_inicio = cliente.get("/inicio")
    respuesta_navegacion = cliente.get("/finanzas/mis-cuotas")

    assert b"Consultar mis cuotas y recibos" in respuesta_inicio.data
    assert b'href="/finanzas/mis-cuotas">Mis cuotas</a>' in (
        respuesta_navegacion.data
    )


def test_inicio_admin_tiene_acceso_rapido_a_finanzas(
    cliente, crear_usuario
):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.get("/inicio")

    assert respuesta.status_code == 200
    assert b'href="/finanzas/movimientos">Finanzas</a>' in respuesta.data
