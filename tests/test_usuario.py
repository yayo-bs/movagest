from datetime import timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensiones import db
from app.models import Usuario


def crear_usuario(email="socia@example.com", **datos):
    usuario = Usuario(email=email, password_hash="hash-de-prueba", **datos)
    db.session.add(usuario)
    return usuario


def test_password_se_guarda_hasheada_y_se_comprueba(app):
    usuario = Usuario(email="socia@example.com")
    usuario.establecer_password("clave-segura")

    assert usuario.password_hash != "clave-segura"
    assert usuario.comprobar_password("clave-segura")
    assert not usuario.comprobar_password("clave-incorrecta")


def test_usuario_tiene_rol_y_estado_por_defecto(app):
    usuario = crear_usuario()
    db.session.commit()

    assert usuario.rol == "socio"
    assert usuario.estado == "pendiente"


def test_email_se_normaliza_y_debe_ser_unico(app):
    crear_usuario(email="Socia@Example.com")
    db.session.commit()

    crear_usuario(email="socia@example.com")
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


@pytest.mark.parametrize("rol", ["invitado", ""])
def test_rol_no_permitido_lanza_error(rol):
    with pytest.raises(ValueError, match="Rol no permitido"):
        Usuario(email="socia@example.com", rol=rol)


@pytest.mark.parametrize("estado", ["baja", ""])
def test_estado_no_permitido_lanza_error(estado):
    with pytest.raises(ValueError, match="Estado no permitido"):
        Usuario(email="socia@example.com", estado=estado)


def test_metodos_de_rol_y_estado(app):
    socio = crear_usuario()
    administradora = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )

    assert not socio.es_administrador()
    assert not socio.esta_activo()
    assert administradora.es_administrador()
    assert administradora.esta_activo()


def test_user_loader_recupera_usuario_por_id(app, cliente):
    usuario = crear_usuario()
    db.session.commit()

    with cliente.session_transaction() as sesion:
        sesion["_user_id"] = str(usuario.id)
        sesion["_fresh"] = True

    respuesta = cliente.get("/")

    assert respuesta.status_code == 200


def test_fecha_alta_usa_utc(app):
    usuario = crear_usuario()
    db.session.flush()

    assert usuario.fecha_alta.tzinfo == timezone.utc
