import pytest

from app import create_app
from app.extensions import db


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
