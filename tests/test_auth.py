"""Pruebas del alta y la autenticación de usuarios.

Cubren el acceso, estados de aprobación y protección de sesión.
"""

import pytest

from app.extensiones import db
from app.models import Usuario


def datos_registro(**cambios):
    datos = {
        "nombre": "Ana",
        "apellidos": "Pérez",
        "email": "ana@example.com",
        "password": "clave-segura-123",
        "repetir_password": "clave-segura-123",
    }
    datos.update(cambios)
    return datos


def test_registro_crea_usuario_pendiente_sin_iniciar_sesion(cliente):
    respuesta = cliente.post(
        "/auth/registro",
        data=datos_registro(),
        follow_redirects=True,
    )

    usuario = db.session.scalar(
        db.select(Usuario).where(Usuario.email == "ana@example.com")
    )
    assert respuesta.status_code == 200
    assert (
        "Solicitud enviada: un administrador debe aprobar tu alta.".encode()
        in respuesta.data
    )
    assert usuario.rol == "socio"
    assert usuario.estado == "pendiente"
    assert cliente.get("/inicio").status_code == 302


def test_registro_rechaza_email_duplicado(cliente, crear_usuario):
    crear_usuario(estado="activo")

    respuesta = cliente.post(
        "/auth/registro",
        data=datos_registro(email="PERSONA@example.com"),
    )

    assert respuesta.status_code == 200
    assert "Ya existe una cuenta".encode() in respuesta.data


def test_registro_rechaza_contrasenas_distintas(cliente):
    respuesta = cliente.post(
        "/auth/registro",
        data=datos_registro(repetir_password="otra-clave-123"),
    )

    assert respuesta.status_code == 200
    assert "Las contraseñas deben coincidir.".encode() in respuesta.data


def test_login_de_usuario_activo(cliente, crear_usuario):
    crear_usuario(estado="activo")

    respuesta = cliente.post(
        "/auth/login",
        data={"email": "PERSONA@example.com", "password": "clave-segura-123"},
    )

    assert respuesta.status_code == 302
    assert respuesta.headers["Location"].endswith("/inicio")
    assert b"Hola, Ana" in cliente.get("/inicio").data


def test_login_redirige_a_ruta_interna_solicitada(cliente, crear_usuario):
    crear_usuario(estado="activo")

    respuesta = cliente.post(
        "/auth/login?next=/auth/registro",
        data={"email": "persona@example.com", "password": "clave-segura-123"},
    )

    assert respuesta.status_code == 302
    assert respuesta.headers["Location"].endswith("/auth/registro")


@pytest.mark.parametrize(
    ("estado", "mensaje"),
    [
        ("pendiente", "Tu alta está pendiente de aprobación."),
        ("rechazado", "Tu solicitud de alta ha sido rechazada."),
        ("baja", "Tu cuenta está de baja y no puedes iniciar sesión."),
    ],
)
def test_login_bloquea_estado_no_activo(cliente, crear_usuario, estado, mensaje):
    crear_usuario(estado=estado)

    respuesta = cliente.post(
        "/auth/login",
        data={"email": "persona@example.com", "password": "clave-segura-123"},
        follow_redirects=True,
    )

    assert respuesta.status_code == 200
    assert mensaje.encode() in respuesta.data
    assert cliente.get("/inicio").status_code == 302


def test_usuario_con_sesion_activa_pierde_acceso_al_darse_de_baja(
    cliente, crear_usuario
):
    usuario = crear_usuario(estado="activo")
    cliente.post(
        "/auth/login",
        data={"email": usuario.email, "password": "clave-segura-123"},
    )
    usuario.estado = "baja"
    db.session.commit()

    respuesta = cliente.get("/inicio")

    assert respuesta.status_code == 302
    assert "/auth/login" in respuesta.headers["Location"]


def test_login_con_contrasena_incorrecta_no_revela_si_existe(
    cliente, crear_usuario
):
    crear_usuario(estado="activo")

    respuesta = cliente.post(
        "/auth/login",
        data={"email": "persona@example.com", "password": "incorrecta"},
        follow_redirects=True,
    )

    assert "Correo electrónico o contraseña incorrectos.".encode() in respuesta.data
    assert b"pendiente" not in respuesta.data
    assert cliente.get("/inicio").status_code == 302


def test_login_con_email_inexistente_usa_mensaje_generico(cliente):
    respuesta = cliente.post(
        "/auth/login",
        data={"email": "no-existe@example.com", "password": "incorrecta"},
        follow_redirects=True,
    )

    assert "Correo electrónico o contraseña incorrectos.".encode() in respuesta.data


def test_inicio_socio_sin_sesion_redirige_a_login(cliente):
    respuesta = cliente.get("/inicio")

    assert respuesta.status_code == 302
    assert "/auth/login?next=%2Finicio" in respuesta.headers["Location"]
    assert b"Inicia sesi\xc3\xb3n" in cliente.get(
        respuesta.headers["Location"]
    ).data


def test_logout_cierra_sesion_y_solo_acepta_post(cliente, crear_usuario):
    crear_usuario(estado="activo")
    cliente.post(
        "/auth/login",
        data={"email": "persona@example.com", "password": "clave-segura-123"},
    )

    assert cliente.get("/auth/logout").status_code == 405
    respuesta = cliente.post("/auth/logout")

    assert respuesta.status_code == 302
    assert respuesta.headers["Location"].endswith("/")
    assert cliente.get("/inicio").status_code == 302


@pytest.mark.parametrize(
    "destino",
    ["https://externo.example", "//externo.example/ruta", "/\\externo.example"],
)
def test_login_rechaza_redireccion_externa(cliente, crear_usuario, destino):
    crear_usuario(estado="activo")

    respuesta = cliente.post(
        f"/auth/login?next={destino}",
        data={"email": "persona@example.com", "password": "clave-segura-123"},
    )

    assert respuesta.status_code == 302
    assert respuesta.headers["Location"].endswith("/inicio")
