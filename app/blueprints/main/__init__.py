"""Blueprint para la página pública principal.

Su ruta raíz presenta la portada de MovaGest.
"""

from flask import Blueprint


bp = Blueprint("main", __name__)

from app.blueprints.main import routes  # noqa: E402,F401
