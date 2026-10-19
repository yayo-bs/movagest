"""Blueprint para administrar talleres e inscripciones.

Agrupa el listado, detalle y acciones de socios y administradores.
"""

from flask import Blueprint


bp = Blueprint("talleres", __name__, url_prefix="/talleres")

from app.talleres import rutas  # noqa: E402,F401
