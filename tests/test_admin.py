"""Pruebas del acceso administrativo y de la revisión de altas.

Verifican permisos, cambios de estado y su efecto sobre el inicio de sesión.
"""

from app.extensiones import db
from app.models import Usuario


def crear_usuario(email, rol="socio", estado="pendiente"):
    usuario = Usuario(
        nombre="Ana",
        apellidos="Pérez",
        email=email,
        rol=rol,
        estado=estado,
    )
    usuario.establecer_password("clave-segura-123")
    db.session.add(usuario)
    db.session.commit()
    return usuario


def iniciar_sesion(cliente, usuario):
    with cliente.session_transaction() as sesion:
        sesion["_user_id"] = str(usuario.id)
        sesion["_fresh"] = True


def test_socio_recibe_403_en_lista_de_altas(app, cliente):
    socio = crear_usuario("socio@example.com", estado="activo")
    iniciar_sesion(cliente, socio)

    respuesta = cliente.get("/admin/altas")

    assert respuesta.status_code == 403


def test_sin_sesion_se_redirige_al_login(cliente):
    respuesta = cliente.get("/admin/altas")

    assert respuesta.status_code == 302
    assert "/auth/login?next=/admin/altas" in respuesta.headers["Location"]


def test_administrador_ve_solicitudes_pendientes(cliente):
    administradora = crear_usuario(
        "admin@example.com", rol="administrador", estado="activo"
    )
    pendiente = crear_usuario("pendiente@example.com")
    iniciar_sesion(cliente, administradora)

    respuesta = cliente.get("/admin/altas")

    assert respuesta.status_code == 200
    assert b"pendiente@example.com" in respuesta.data
    assert b"Aprobar" in respuesta.data
    assert b"Rechazar" in respuesta.data
    assert pendiente.estado == "pendiente"


def test_aprobar_activa_usuario_y_permita_iniciar_sesion(app, cliente):
    administradora = crear_usuario(
        "admin@example.com", rol="administrador", estado="activo"
    )
    pendiente = crear_usuario("pendiente@example.com")
    iniciar_sesion(cliente, administradora)

    respuesta = cliente.post(f"/admin/altas/{pendiente.id}/aprobar")

    assert respuesta.status_code == 302
    assert db.session.get(Usuario, pendiente.id).estado == "activo"

    cliente_socio = app.test_client()
    respuesta_login = cliente_socio.post(
        "/auth/login",
        data={
            "email": "pendiente@example.com",
            "password": "clave-segura-123",
        },
    )
    assert respuesta_login.status_code == 302
    assert b"Hola, Ana" in cliente_socio.get("/auth/inicio").data


def test_rechazar_no_permite_iniciar_sesion(cliente):
    administradora = crear_usuario(
        "admin@example.com", rol="administrador", estado="activo"
    )
    pendiente = crear_usuario("pendiente@example.com")
    iniciar_sesion(cliente, administradora)

    respuesta = cliente.post(f"/admin/altas/{pendiente.id}/rechazar")

    assert respuesta.status_code == 302
    assert db.session.get(Usuario, pendiente.id).estado == "rechazado"

    cliente.post("/auth/logout")
    respuesta_login = cliente.post(
        "/auth/login",
        data={
            "email": "pendiente@example.com",
            "password": "clave-segura-123",
        },
        follow_redirects=True,
    )
    assert respuesta_login.status_code == 200
    assert "Tu solicitud de alta ha sido rechazada.".encode() in respuesta_login.data
    assert cliente.get("/auth/inicio").status_code == 302


def test_aprobar_usuario_no_pendiente_no_cambia_estado(cliente):
    administradora = crear_usuario(
        "admin@example.com", rol="administrador", estado="activo"
    )
    activo = crear_usuario("activo@example.com", estado="activo")
    iniciar_sesion(cliente, administradora)

    respuesta = cliente.post(f"/admin/altas/{activo.id}/aprobar", follow_redirects=True)

    assert respuesta.status_code == 200
    assert db.session.get(Usuario, activo.id).estado == "activo"
    assert "La solicitud ya no está pendiente.".encode() in respuesta.data


def test_alta_inexistente_responde_404(cliente):
    administradora = crear_usuario(
        "admin@example.com", rol="administrador", estado="activo"
    )
    iniciar_sesion(cliente, administradora)

    assert cliente.post("/admin/altas/999/aprobar").status_code == 404
