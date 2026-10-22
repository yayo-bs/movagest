"""Pruebas de los recibos PDF de cuotas.

Verifican generación, descarga y permisos para socios y administradores.
"""

from datetime import date
from decimal import Decimal

import pytest
from flask import g

from app.extensiones import db
from app.models import Cuota


def iniciar_sesion(cliente, usuario):
    g.pop("_login_user", None)
    with cliente.session_transaction() as sesion:
        sesion["_user_id"] = str(usuario.id)
        sesion["_fresh"] = True


def crear_cuota(usuario, estado="pagada", numero_recibo="R-2026-0001"):
    cuota = Cuota(
        usuario=usuario,
        periodo=2026,
        importe=Decimal("1234.56"),
        estado=estado,
        fecha_pago=date(2026, 6, 15) if estado == "pagada" else None,
        numero_recibo=numero_recibo,
    )
    db.session.add(cuota)
    db.session.commit()
    return cuota


def test_descarga_recibo_devuelve_pdf_y_nombre_basado_en_numero(
    cliente, crear_usuario, app
):
    app.config["NOMBRE_ASOCIACION"] = "Asociación Cultural"
    socia = crear_usuario(
        email="socia@example.com",
        nombre="Lucía",
        apellidos="Pérez",
        estado="activo",
    )
    cuota = crear_cuota(socia)
    iniciar_sesion(cliente, socia)

    respuesta = cliente.get(f"/finanzas/cuotas/{cuota.id}/recibo")

    assert respuesta.status_code == 200
    assert respuesta.mimetype == "application/pdf"
    assert respuesta.data.startswith(b"%PDF")
    assert respuesta.headers["Content-Disposition"].endswith(
        'filename=R-2026-0001.pdf'
    )


def test_socio_descarga_su_recibo_y_administrador_cualquier_recibo(
    cliente, crear_usuario
):
    socia = crear_usuario(
        email="socia@example.com",
        estado="activo",
    )
    otra_socia = crear_usuario(
        email="otra@example.com",
        estado="activo",
    )
    cuota_socia = crear_cuota(socia)
    cuota_ajena = crear_cuota(otra_socia, numero_recibo="R-2026-0002")
    iniciar_sesion(cliente, socia)

    recibo_propio = cliente.get(
        f"/finanzas/cuotas/{cuota_socia.id}/recibo"
    )
    recibo_ajeno = cliente.get(
        f"/finanzas/cuotas/{cuota_ajena.id}/recibo"
    )

    assert recibo_propio.status_code == 200
    assert recibo_ajeno.status_code == 404

    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    iniciar_sesion(cliente, administrador)
    respuesta_admin = cliente.get(
        f"/finanzas/cuotas/{cuota_ajena.id}/recibo"
    )

    assert respuesta_admin.status_code == 200
    assert respuesta_admin.mimetype == "application/pdf"


@pytest.mark.parametrize("estado", ["pendiente", "anulada"])
def test_cuota_no_pagada_no_tiene_recibo_descargable(
    cliente, crear_usuario, estado
):
    socia = crear_usuario(
        email=f"{estado}@example.com",
        estado="activo",
    )
    cuota = crear_cuota(socia, estado=estado)
    iniciar_sesion(cliente, socia)

    respuesta = cliente.get(f"/finanzas/cuotas/{cuota.id}/recibo")

    assert respuesta.status_code == 404


def test_usuario_anonimo_no_puede_descargar_recibo(cliente, crear_usuario):
    socia = crear_usuario(email="socia@example.com", estado="activo")
    cuota = crear_cuota(socia)

    respuesta = cliente.get(f"/finanzas/cuotas/{cuota.id}/recibo")

    assert respuesta.status_code == 302
    assert respuesta.headers["Location"].startswith("/auth/login?next=")
