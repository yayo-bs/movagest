"""Pruebas de confirmaciones, errores y estados vacíos de la fase de cierre.

Comprueban que las pantallas mantienen sus acciones y mensajes de seguridad.
"""

import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.extensiones import db
from app.models import (
    Asamblea,
    Cuota,
    Documento,
    Movimiento,
    Noticia,
    Taller,
    Usuario,
)
from tests.conftest import iniciar_sesion


def _comprobar_formulario_confirmado(respuesta, ruta):
    """Exige confirmación en el formulario que publica la acción indicada."""
    formularios = re.findall(
        r"<form\b[^>]*>", respuesta.get_data(as_text=True)
    )
    for formulario in formularios:
        if f'action="{ruta}"' in formulario:
            assert 'data-confirmar="' in formulario
            return
    raise AssertionError(f"No se encontró un formulario confirmado para {ruta}")


def test_formularios_destructivos_muestran_confirmacion(
    cliente, crear_usuario
):
    administrador = crear_usuario(
        email="admin@example.com",
        nombre="Lucía",
        apellidos="García",
        rol="administrador",
        estado="activo",
    )
    socio = crear_usuario(
        email="socio@example.com",
        nombre="Ana",
        apellidos="Pérez",
        estado="activo",
    )
    rechazado = crear_usuario(
        email="rechazado@example.com",
        nombre="Luis",
        apellidos="Díaz",
        estado="rechazado",
    )
    noticia = Noticia(
        titulo="Festival anual",
        contenido="Información",
        autor=administrador,
    )
    documento = Documento(
        titulo="Presupuesto",
        categoria="documento",
        nombre_original="presupuesto.pdf",
        nombre_archivo="presupuesto.pdf",
        subido_por=administrador,
    )
    acta = Documento(
        titulo="Acta de junio",
        categoria="acta",
        nombre_original="acta.pdf",
        nombre_archivo="acta.pdf",
        subido_por=administrador,
    )
    taller = Taller(
        titulo="Danza tradicional",
        descripcion="Taller de prueba",
        fecha_hora=datetime.now(timezone.utc) + timedelta(days=10),
        lugar="Sala principal",
        plazas=10,
        creado_por=administrador,
    )
    asamblea = Asamblea(
        titulo="Asamblea de otoño",
        tipo="ordinaria",
        fecha_hora=datetime.now(timezone.utc) + timedelta(days=20),
        lugar="Centro cultural",
        orden_del_dia="Presupuesto",
        autor=administrador,
    )
    cuota_pendiente = Cuota(
        usuario=socio,
        periodo=2025,
        importe=Decimal("25.00"),
        estado="pendiente",
    )
    cuota_pagada = Cuota(
        usuario=socio,
        periodo=2026,
        importe=Decimal("25.00"),
        estado="pagada",
        fecha_pago=date.today(),
        numero_recibo="R-2026-0001",
    )
    movimiento = Movimiento(
        tipo="ingreso",
        concepto="Festival de verano",
        importe=Decimal("50.00"),
        fecha=date.today(),
    )
    db.session.add_all(
        [
            noticia,
            documento,
            acta,
            taller,
            asamblea,
            cuota_pendiente,
            cuota_pagada,
            movimiento,
        ]
    )
    db.session.commit()
    iniciar_sesion(cliente, administrador)

    respuestas_y_rutas = [
        (
            cliente.get("/admin/altas"),
            f"/admin/usuarios/{socio.id}/dar-baja",
        ),
        (
            cliente.get("/admin/altas"),
            f"/admin/altas/{rechazado.id}/eliminar",
        ),
        (
            cliente.get(f"/noticias/{noticia.id}"),
            f"/noticias/{noticia.id}/borrar",
        ),
        (
            cliente.get("/documentos/"),
            f"/documentos/{documento.id}/borrar",
        ),
        (
            cliente.get("/documentos/"),
            f"/documentos/{acta.id}/borrar",
        ),
        (
            cliente.get(f"/talleres/{taller.id}"),
            f"/talleres/{taller.id}/borrar",
        ),
        (
            cliente.get(f"/asambleas/{asamblea.id}"),
            f"/asambleas/{asamblea.id}/eliminar",
        ),
        (
            cliente.get("/finanzas/cuotas"),
            f"/finanzas/cuotas/{cuota_pendiente.id}/eliminar",
        ),
        (
            cliente.get("/finanzas/cuotas"),
            f"/finanzas/cuotas/{cuota_pagada.id}/anular",
        ),
        (
            cliente.get("/finanzas/movimientos"),
            f"/finanzas/movimientos/{movimiento.id}/eliminar",
        ),
    ]

    for respuesta, ruta in respuestas_y_rutas:
        assert respuesta.status_code == 200
        _comprobar_formulario_confirmado(respuesta, ruta)


def test_pagina_404_usa_plantilla_personalizada(cliente):
    respuesta = cliente.get("/ruta-que-no-existe")

    assert respuesta.status_code == 404
    assert "Página no encontrada".encode() in respuesta.data
    assert b"Volver al inicio" in respuesta.data


def test_socio_403_usa_plantilla_personalizada(
    cliente, crear_usuario
):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    iniciar_sesion(cliente, socio)

    respuesta = cliente.get("/admin/altas")

    assert respuesta.status_code == 403
    assert "No tienes permiso para ver esta página".encode() in respuesta.data


def test_error_500_no_filtra_detalles_y_revierte_sesion(app, cliente):
    @app.get("/__prueba_error_500")
    def provocar_error():
        db.session.add(Usuario(email="incompleto@example.com"))
        db.session.flush()
        return "Esta respuesta no debe alcanzarse"

    app.config["PROPAGATE_EXCEPTIONS"] = False

    respuesta = cliente.get("/__prueba_error_500")

    assert respuesta.status_code == 500
    assert b"Error interno" in respuesta.data
    assert b"Traceback" not in respuesta.data
    assert b"incompleto@example.com" not in respuesta.data
    assert db.session.scalar(select(db.func.count(Usuario.id))) == 0


def test_movimientos_sin_datos_muestra_estado_y_totales_a_cero(
    cliente, crear_usuario
):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.get("/finanzas/movimientos")

    assert respuesta.status_code == 200
    assert b"No hay movimientos registrados para este periodo." in respuesta.data
    assert b"/finanzas/movimientos/nuevo" in respuesta.data
    assert respuesta.data.count("0,00 \u20ac".encode()) >= 4


def test_movimientos_con_filtros_sin_resultados_muestra_estado_unificado(
    cliente, crear_usuario
):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.get("/finanzas/movimientos?q=sin-resultados")

    assert respuesta.status_code == 200
    assert b"No hay resultados con estos filtros." in respuesta.data
    assert respuesta.data.count("0,00 \u20ac".encode()) >= 4
