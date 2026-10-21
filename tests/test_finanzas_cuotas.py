"""Pruebas de la gestión administrativa de cuotas.

Comprueban permisos, generación idempotente y transiciones de estado.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.extensiones import db
from app.models import Cuota


def iniciar_sesion(cliente, usuario):
    with cliente.session_transaction() as sesion:
        sesion["_user_id"] = str(usuario.id)
        sesion["_fresh"] = True


def crear_cuota(usuario, **cambios):
    datos = {
        "usuario": usuario,
        "periodo": 2026,
        "importe": Decimal("25.00"),
    }
    datos.update(cambios)
    cuota = Cuota(**datos)
    db.session.add(cuota)
    db.session.commit()
    return cuota


def test_socio_no_accede_a_rutas_de_gestion(cliente, crear_usuario):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    cuota = crear_cuota(socio)
    iniciar_sesion(cliente, socio)

    respuestas = [
        cliente.get("/finanzas/cuotas"),
        cliente.get("/finanzas/cuotas/generar"),
        cliente.post("/finanzas/cuotas/generar"),
        cliente.get(f"/finanzas/cuotas/{cuota.id}/editar"),
        cliente.post(f"/finanzas/cuotas/{cuota.id}/pagar"),
        cliente.post(f"/finanzas/cuotas/{cuota.id}/eliminar"),
        cliente.post(f"/finanzas/cuotas/{cuota.id}/anular"),
    ]

    assert [respuesta.status_code for respuesta in respuestas] == [403] * 7


def test_usuario_anonimo_se_redirige_al_login(cliente):
    respuesta = cliente.get("/finanzas/cuotas")

    assert respuesta.status_code == 302
    assert respuesta.headers["Location"].startswith("/auth/login?next=")


def test_generar_cuotas_crea_solo_para_socios_activos_y_es_idempotente(
    cliente, crear_usuario
):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    socio_activo = crear_usuario(
        email="socio@example.com",
        estado="activo",
    )
    crear_usuario(email="pendiente@example.com", estado="pendiente")
    iniciar_sesion(cliente, administrador)
    datos = {"periodo": "2026", "importe": "35.50"}

    primera = cliente.post(
        "/finanzas/cuotas/generar",
        data=datos,
        follow_redirects=True,
    )
    segunda = cliente.post(
        "/finanzas/cuotas/generar",
        data=datos,
        follow_redirects=True,
    )
    cuotas = db.session.scalars(db.select(Cuota)).all()

    assert len(cuotas) == 1
    assert cuotas[0].usuario_id == socio_activo.id
    assert cuotas[0].importe == Decimal("35.50")
    assert "Se han creado 1 cuotas pendientes.".encode() in primera.data
    assert "Se han creado 0 cuotas pendientes.".encode() in segunda.data


def test_generacion_conserva_cuota_existente_del_periodo(
    cliente, crear_usuario
):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    socio = crear_usuario(email="socio@example.com", estado="activo")
    existente = crear_cuota(socio, importe=Decimal("20.00"))
    iniciar_sesion(cliente, administrador)

    cliente.post(
        "/finanzas/cuotas/generar",
        data={"periodo": "2026", "importe": "35.50"},
    )

    cuotas = db.session.scalars(db.select(Cuota)).all()
    assert len(cuotas) == 1
    assert cuotas[0].id == existente.id
    assert cuotas[0].importe == Decimal("20.00")


def test_listado_filtra_por_estado_periodo_y_busqueda(
    cliente, crear_usuario
):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    socia = crear_usuario(
        email="ana@example.com",
        nombre="Ana",
        apellidos="Danza",
        estado="activo",
    )
    cuota = crear_cuota(socia)
    crear_cuota(
        crear_usuario(
            email="otra@example.com",
            nombre="Lucía",
            apellidos="Ritmo",
            estado="activo",
        ),
        periodo=2025,
        estado="pagada",
        fecha_pago=date(2025, 6, 1),
        numero_recibo="R-2025-0001",
    )
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.get(
        "/finanzas/cuotas?q=ana&estado=pendiente&periodo=2026"
    )

    assert respuesta.status_code == 200
    assert b"ana@example.com" in respuesta.data
    assert b"otra@example.com" not in respuesta.data
    assert cuota.id is not None


def test_pago_asigna_recibos_correlativos_segun_anio_fecha_pago(
    cliente, crear_usuario
):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    primera_socia = crear_usuario(
        email="primera@example.com",
        estado="activo",
    )
    segunda_socia = crear_usuario(
        email="segunda@example.com",
        estado="activo",
    )
    primera_cuota = crear_cuota(primera_socia)
    segunda_cuota = crear_cuota(segunda_socia)
    iniciar_sesion(cliente, administrador)

    respuesta_primera = cliente.post(
        f"/finanzas/cuotas/{primera_cuota.id}/pagar",
        data={"fecha_pago": "2025-12-20"},
    )
    respuesta_segunda = cliente.post(
        f"/finanzas/cuotas/{segunda_cuota.id}/pagar",
        data={"fecha_pago": "2025-12-21"},
    )

    assert respuesta_primera.status_code == 302
    assert respuesta_segunda.status_code == 302
    assert primera_cuota.estado == "pagada"
    assert primera_cuota.fecha_pago == date(2025, 12, 20)
    assert primera_cuota.numero_recibo == "R-2025-0001"
    assert segunda_cuota.numero_recibo == "R-2025-0002"


def test_fecha_de_pago_futura_no_cambia_la_cuota(
    cliente, crear_usuario
):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    socio = crear_usuario(email="socio@example.com", estado="activo")
    cuota = crear_cuota(socio)
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.post(
        f"/finanzas/cuotas/{cuota.id}/pagar",
        data={"fecha_pago": "2099-01-01"},
    )

    assert respuesta.status_code == 200
    assert b"La fecha de pago no puede ser futura." in respuesta.data
    assert cuota.estado == "pendiente"
    assert cuota.numero_recibo is None


def test_solo_se_pueden_editar_y_eliminar_cuotas_pendientes(
    cliente, crear_usuario
):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    socio = crear_usuario(email="socio@example.com", estado="activo")
    cuota_pendiente = crear_cuota(socio)
    cuota_pagada = crear_cuota(
        crear_usuario(
            email="pagada@example.com",
            estado="activo",
        ),
        estado="pagada",
        fecha_pago=date(2026, 1, 10),
        numero_recibo="R-2026-0001",
    )
    iniciar_sesion(cliente, administrador)

    editar_pagada = cliente.post(
        f"/finanzas/cuotas/{cuota_pagada.id}/editar",
        data={"importe": "99.00"},
        follow_redirects=True,
    )
    eliminar_pagada = cliente.post(
        f"/finanzas/cuotas/{cuota_pagada.id}/eliminar",
        follow_redirects=True,
    )
    eliminar_pendiente = cliente.post(
        f"/finanzas/cuotas/{cuota_pendiente.id}/eliminar"
    )

    assert cuota_pagada.importe == Decimal("25.00")
    assert cuota_pagada.estado == "pagada"
    assert "Solo se puede editar".encode() in editar_pagada.data
    assert "Solo se pueden eliminar".encode() in eliminar_pagada.data
    assert db.session.get(Cuota, cuota_pagada.id) is not None
    assert db.session.get(Cuota, cuota_pendiente.id) is None


def test_editar_importe_de_cuota_pendiente(cliente, crear_usuario):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    socio = crear_usuario(email="socio@example.com", estado="activo")
    cuota = crear_cuota(socio)
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.post(
        f"/finanzas/cuotas/{cuota.id}/editar",
        data={"importe": "42.75"},
        follow_redirects=True,
    )

    assert respuesta.status_code == 200
    assert cuota.importe == Decimal("42.75")
    assert cuota.estado == "pendiente"


def test_anular_conserva_recibo_y_no_permite_transiciones_invalidas(
    cliente, crear_usuario
):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    cuota_pendiente = crear_cuota(
        crear_usuario(
            email="pendiente@example.com",
            estado="activo",
        )
    )
    cuota_pagada = crear_cuota(
        crear_usuario(
            email="pagada@example.com",
            estado="activo",
        ),
        estado="pagada",
        fecha_pago=date(2026, 1, 10),
        numero_recibo="R-2026-0001",
    )
    iniciar_sesion(cliente, administrador)

    intento_anular_pendiente = cliente.post(
        f"/finanzas/cuotas/{cuota_pendiente.id}/anular",
        follow_redirects=True,
    )
    intento_pagar_pagada = cliente.post(
        f"/finanzas/cuotas/{cuota_pagada.id}/pagar",
        follow_redirects=True,
    )
    cliente.post(f"/finanzas/cuotas/{cuota_pagada.id}/anular")

    assert "Solo se pueden anular".encode() in intento_anular_pendiente.data
    assert "Solo se puede pagar".encode() in intento_pagar_pagada.data
    assert cuota_pendiente.estado == "pendiente"
    assert cuota_pagada.estado == "anulada"
    assert cuota_pagada.numero_recibo == "R-2026-0001"


@pytest.mark.parametrize(
    "importe",
    ["0", "-1.00", "texto", "NaN", "Infinity", "100000000.00"],
)
def test_generacion_rechaza_importe_no_positivo_o_no_decimal(
    cliente, crear_usuario, importe
):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.post(
        "/finanzas/cuotas/generar",
        data={"periodo": "2026", "importe": importe},
    )

    assert respuesta.status_code == 200
    assert db.session.scalar(db.select(Cuota)) is None
