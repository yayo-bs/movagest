"""Fixtures de aplicación y cliente HTTP para las pruebas.

Cada prueba usa una base de datos en memoria y una carpeta temporal.
"""

import os

import pytest
from flask import g, has_app_context

from app import create_app
from app.extensiones import db
from app.models import Usuario


def iniciar_sesion(cliente, usuario):
    """Inicia sesión con el cliente y descarta el usuario cacheado de Flask-Login."""
    if has_app_context():
        g.pop("_login_user", None)
    with cliente.session_transaction() as sesion:
        sesion["_user_id"] = str(usuario.id)
        sesion["_fresh"] = True


@pytest.fixture
def app(tmp_path):
    """Prepara una app con base de datos y subidas aisladas."""
    aplicacion = create_app("testing")
    aplicacion.config["CARPETA_SUBIDAS"] = str(tmp_path / "subidas")
    os.makedirs(aplicacion.config["CARPETA_SUBIDAS"], exist_ok=True)

    with aplicacion.app_context():
        db.create_all()
        yield aplicacion
        db.drop_all()


@pytest.fixture
def cliente(app):
    """Proporciona el cliente HTTP de pruebas de Flask."""
    return app.test_client()


@pytest.fixture
def crear_usuario():
    """Crea usuarios de prueba con opciones comunes para toda la suite."""

    def _crear_usuario(
        email="persona@example.com",
        nombre="Ana",
        apellidos="Pérez",
        rol=None,
        estado=None,
        contrasena="clave-segura-123",
        confirmar=True,
    ):
        datos = {
            "nombre": nombre,
            "apellidos": apellidos,
            "email": email,
        }
        if rol is not None:
            datos["rol"] = rol
        if estado is not None:
            datos["estado"] = estado

        usuario = Usuario(**datos)
        usuario.establecer_password(contrasena)
        db.session.add(usuario)
        if confirmar:
            db.session.commit()
        return usuario

    return _crear_usuario
