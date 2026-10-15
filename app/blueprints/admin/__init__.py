"""Blueprint de administración de MovaGest.

Agrupa las rutas reservadas al equipo administrador de la asociación.
"""

from flask import Blueprint


bp = Blueprint("admin", __name__, url_prefix="/admin")

from app.blueprints.admin import routes  # noqa: E402,F401
