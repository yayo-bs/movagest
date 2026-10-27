"""Pruebas del historial mínimo de actividad.

Comprueban el helper, la conservación del historial y su integración por área.
"""

from datetime import datetime, timedelta, timezone
from io import BytesIO

from flask_login import login_user

from app.extensiones import db
from app.models import Actividad, Usuario
from app.utilidades.actividad import registrar
from tests.conftest import iniciar_sesion


def obtener_actividad(accion):
    return db.session.scalar(
        db.select(Actividad).where(Actividad.accion == accion)
    )


def test_registrar_guarda_usuario_nombre_y_fecha(app, crear_usuario):
    usuario = crear_usuario(
        email="admin@example.com",
        nombre="Lucía",
        apellidos="García",
        rol="administrador",
        estado="activo",
    )

    with app.test_request_context("/"):
        login_user(usuario)
        antes = datetime.now(timezone.utc)
        registrar("noticia.crear", "Creada una noticia")
        db.session.commit()
        despues = datetime.now(timezone.utc)

    actividad = obtener_actividad("noticia.crear")
    assert actividad is not None
    assert actividad.usuario_id == usuario.id
    assert actividad.usuario_nombre == "Lucía García"
    assert antes <= actividad.fecha.replace(tzinfo=timezone.utc) <= despues


def test_registrar_sin_usuario_autenticado_usa_sistema(app):
    with app.test_request_context("/"):
        registrar("sistema.prueba", "Acción sin usuario")
        db.session.commit()

    actividad = obtener_actividad("sistema.prueba")
    assert actividad is not None
    assert actividad.usuario_id is None
    assert actividad.usuario_nombre == "Sistema"


def test_fallo_al_registrar_no_impide_la_accion_principal(
    app, cliente, crear_usuario, monkeypatch
):
    from app.models import Noticia

    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    iniciar_sesion(cliente, administrador)
    agregar_original = db.session.add

    def agregar_con_fallo(instancia, *args, **kwargs):
        if isinstance(instancia, Actividad):
            raise RuntimeError("Fallo simulado al guardar el historial")
        return agregar_original(instancia, *args, **kwargs)

    monkeypatch.setattr(db.session, "add", agregar_con_fallo)

    respuesta = cliente.post(
        "/noticias/nueva",
        data={"titulo": "Noticia conservada", "contenido": "Contenido"},
    )

    assert respuesta.status_code == 302
    assert db.session.scalar(
        db.select(Noticia).where(Noticia.titulo == "Noticia conservada")
    ) is not None
    assert obtener_actividad("noticia.crear") is None


def test_integracion_usuarios_registra_aprobacion(cliente, crear_usuario):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    socio = crear_usuario(email="socio@example.com", estado="pendiente")
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.post(f"/admin/altas/{socio.id}/aprobar")

    assert respuesta.status_code == 302
    actividad = obtener_actividad("socio.aprobar")
    assert actividad.usuario_id == administrador.id
    assert "Ana Pérez" in actividad.descripcion


def test_integracion_noticias_registra_creacion(cliente, crear_usuario):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.post(
        "/noticias/nueva",
        data={"titulo": "Noticia registrada", "contenido": "Contenido"},
    )

    assert respuesta.status_code == 302
    actividad = obtener_actividad("noticia.crear")
    assert actividad.usuario_id == administrador.id
    assert "Noticia registrada" in actividad.descripcion


def test_integracion_documentos_registra_subida(
    app, cliente, crear_usuario
):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.post(
        "/documentos/nuevo",
        data={
            "titulo": "Acta archivada",
            "descripcion": "Acta de reunión",
            "categoria": "acta",
            "archivo": (BytesIO(b"%PDF-1.4\ncontenido pdf"), "acta.pdf"),
        },
        content_type="multipart/form-data",
    )

    assert respuesta.status_code == 302
    actividad = obtener_actividad("documento.subir")
    assert actividad.usuario_id == administrador.id
    assert "Acta archivada" in actividad.descripcion


def test_integracion_talleres_registra_creacion(cliente, crear_usuario):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.post(
        "/talleres/nuevo",
        data={
            "titulo": "Taller registrado",
            "descripcion": "Danza contemporánea",
            "fecha_hora": "2030-01-01T12:00",
            "lugar": "Sala principal",
            "plazas": "8",
        },
    )

    assert respuesta.status_code == 302
    actividad = obtener_actividad("taller.crear")
    assert actividad.usuario_id == administrador.id
    assert "Taller registrado" in actividad.descripcion


def test_integracion_asambleas_registra_creacion(cliente, crear_usuario):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    fecha = (datetime.now(timezone.utc) + timedelta(days=5)).strftime(
        "%Y-%m-%dT%H:%M"
    )
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.post(
        "/asambleas/nueva",
        data={
            "titulo": "Asamblea registrada",
            "tipo": "ordinaria",
            "fecha_hora": fecha,
            "lugar": "Centro cultural",
            "orden_del_dia": "Presupuesto anual",
        },
    )

    assert respuesta.status_code == 302
    actividad = obtener_actividad("asamblea.crear")
    assert actividad.usuario_id == administrador.id
    assert "Asamblea registrada" in actividad.descripcion


def test_integracion_cuotas_registra_generacion(cliente, crear_usuario):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    crear_usuario(
        email="socio@example.com",
        rol="socio",
        estado="activo",
    )
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.post(
        "/finanzas/cuotas/generar",
        data={"periodo": "2030", "importe": "25.00"},
    )

    assert respuesta.status_code == 302
    actividad = obtener_actividad("cuota.generar")
    assert actividad.usuario_id == administrador.id
    assert "periodo 2030" in actividad.descripcion


def test_integracion_movimientos_registra_creacion(cliente, crear_usuario):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.post(
        "/finanzas/movimientos/nuevo",
        data={
            "tipo": "ingreso",
            "concepto": "Donación registrada",
            "importe": "50.00",
            "fecha": datetime.now().date().isoformat(),
            "categoria": "Donaciones",
        },
    )

    assert respuesta.status_code == 302
    actividad = obtener_actividad("movimiento.crear")
    assert actividad.usuario_id == administrador.id
    assert "Donación registrada" in actividad.descripcion


def test_borrar_usuario_conserva_su_historial(
    app, crear_usuario
):
    usuario = crear_usuario(
        email="persona@example.com",
        nombre="Nombre",
        apellidos="Conservado",
        estado="activo",
    )
    actividad = Actividad(
        usuario=usuario,
        usuario_nombre="Nombre Conservado",
        accion="socio.prueba",
        descripcion="Historial conservado",
    )
    db.session.add(actividad)
    db.session.commit()
    id_actividad = actividad.id

    db.session.delete(usuario)
    db.session.commit()

    actividad_conservada = db.session.get(Actividad, id_actividad)
    assert actividad_conservada.usuario_id is None
    assert actividad_conservada.usuario_nombre == "Nombre Conservado"
