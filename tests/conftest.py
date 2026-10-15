"""Fixtures de aplicación y cliente HTTP para las pruebas.

Cada prueba recibe una base de datos aislada en memoria.
"""

import pytest

from app import create_app
from app.extensiones import db
from app.models import Usuario


@pytest.fixture
def app():
    """Prepara una aplicación aislada con una base de datos en memoria."""
    aplicacion = create_app("testing")

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
