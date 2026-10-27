"""Pruebas del listado de actividad reservado a administración.

Verifican permisos, filtros, orden, paginación y que la vista sea de solo lectura.
"""

from datetime import datetime, timedelta, timezone

from flask import g

from app.extensiones import db
from app.models import Actividad


def iniciar_sesion(cliente, usuario):
    with cliente.session_transaction() as sesion:
        sesion["_user_id"] = str(usuario.id)
        sesion["_fresh"] = True


def crear_actividad(accion, descripcion, usuario_nombre, fecha=None, usuario=None):
    actividad = Actividad(
        accion=accion,
        descripcion=descripcion,
        usuario_nombre=usuario_nombre,
        fecha=fecha or datetime.now(timezone.utc),
        usuario=usuario,
    )
    db.session.add(actividad)
    db.session.commit()
    return actividad


def crear_administrador(crear_usuario):
    return crear_usuario(
        email="admin@example.com",
        nombre="Admin",
        apellidos="Prueba",
        rol="administrador",
        estado="activo",
    )


def test_administrador_ve_el_registro_de_actividad(
    cliente, crear_usuario
):
    administrador = crear_administrador(crear_usuario)
    crear_actividad(
        "noticia.crear",
        "Creada una noticia",
        "Admin Prueba",
        usuario=administrador,
    )
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.get("/admin/actividad")

    assert respuesta.status_code == 200
    assert b"Registro de actividad" in respuesta.data
    assert b"Creada una noticia" in respuesta.data
    assert b"Noticia" in respuesta.data
    assert b"Fecha y hora" in respuesta.data


def test_socio_recibe_403_y_anonimo_es_redirigido(
    app, cliente, crear_usuario
):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    iniciar_sesion(cliente, socio)

    respuesta_socio = cliente.get("/admin/actividad")
    g.pop("_login_user", None)
    respuesta_anonima = app.test_client().get("/admin/actividad")

    assert respuesta_socio.status_code == 403
    assert respuesta_anonima.status_code == 302
    assert respuesta_anonima.headers["Location"].startswith(
        "/auth/login?next="
    )


def test_orden_predeterminado_y_ascendente(cliente, crear_usuario):
    administrador = crear_administrador(crear_usuario)
    fecha_antigua = datetime.now(timezone.utc) - timedelta(days=2)
    fecha_reciente = datetime.now(timezone.utc) - timedelta(days=1)
    crear_actividad("noticia.crear", "Acción antigua", "Admin", fecha_antigua)
    crear_actividad("noticia.editar", "Acción reciente", "Admin", fecha_reciente)
    iniciar_sesion(cliente, administrador)

    descendente = cliente.get("/admin/actividad")
    ascendente = cliente.get("/admin/actividad?orden=fecha&dir=asc")

    assert descendente.data.index(b"Acci\xc3\xb3n reciente") < descendente.data.index(
        b"Acci\xc3\xb3n antigua"
    )
    assert ascendente.data.index(b"Acci\xc3\xb3n antigua") < ascendente.data.index(
        b"Acci\xc3\xb3n reciente"
    )


def test_busqueda_encuentra_descripcion_y_nombre_de_usuario(
    cliente, crear_usuario
):
    administrador = crear_administrador(crear_usuario)
    crear_actividad(
        "documento.subir", "Se publicó el acta anual", "Ana Pérez"
    )
    crear_actividad(
        "taller.crear", "Se organizó una actividad", "Luis García"
    )
    iniciar_sesion(cliente, administrador)

    por_descripcion = cliente.get("/admin/actividad?q=acta+anual")
    por_usuario = cliente.get("/admin/actividad?q=Luis+Garc%C3%ADa")

    assert b"Se public\xc3\xb3 el acta anual" in por_descripcion.data
    assert b"Se organiz\xc3\xb3 una actividad" not in por_descripcion.data
    assert b"Luis Garc\xc3\xada" in por_usuario.data
    assert b"Se public\xc3\xb3 el acta anual" not in por_usuario.data


def test_filtros_por_area_y_usuario(cliente, crear_usuario):
    administrador = crear_administrador(crear_usuario)
    crear_actividad("noticia.crear", "Noticia de Ana", "Ana Pérez")
    crear_actividad("taller.crear", "Taller de Ana", "Ana Pérez")
    crear_actividad("noticia.editar", "Noticia de Luis", "Luis García")
    iniciar_sesion(cliente, administrador)

    por_area = cliente.get("/admin/actividad?area=taller")
    por_usuario = cliente.get(
        "/admin/actividad?usuario=Luis+Garc%C3%ADa"
    )

    assert b"Taller de Ana" in por_area.data
    assert b"Noticia de Ana" not in por_area.data
    assert b"Noticia de Luis" in por_usuario.data
    assert b"Noticia de Ana" not in por_usuario.data
    assert b"Taller de Ana" not in por_usuario.data


def test_paginacion_respeta_por_pagina(cliente, app, crear_usuario):
    administrador = crear_administrador(crear_usuario)
    app.config["POR_PAGINA"] = 2
    for numero in range(5):
        crear_actividad(
            "noticia.crear",
            f"Registro {numero}",
            "Admin",
            datetime.now(timezone.utc) + timedelta(minutes=numero),
        )
    iniciar_sesion(cliente, administrador)

    primera = cliente.get("/admin/actividad")
    segunda = cliente.get("/admin/actividad?pagina=2")

    assert b"Registro 4" in primera.data
    assert b"Registro 3" in primera.data
    assert b"Registro 2" not in primera.data
    assert b"P\xc3\xa1gina 1 de 3" in primera.data
    assert b"Registro 2" in segunda.data
    assert b"Registro 1" in segunda.data
    assert b"Registro 0" not in segunda.data


def test_estados_vacios_con_y_sin_filtros(cliente, crear_usuario):
    administrador = crear_administrador(crear_usuario)
    iniciar_sesion(cliente, administrador)

    vacio = cliente.get("/admin/actividad")
    sin_resultados = cliente.get("/admin/actividad?area=socio")

    assert b"Todav\xc3\xada no hay actividad registrada." in vacio.data
    assert b"No hay resultados con estos filtros." in sin_resultados.data


def test_vista_no_acepta_post(cliente, crear_usuario):
    administrador = crear_administrador(crear_usuario)
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.post("/admin/actividad")

    assert respuesta.status_code == 405
