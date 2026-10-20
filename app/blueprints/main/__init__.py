"""Blueprint para las páginas generales de MovaGest.

Incluye la home pública y el inicio de las cuentas autenticadas.
"""

from flask import Blueprint


bp = Blueprint("main", __name__)

from app.blueprints.main import routes  # noqa: E402,F401
