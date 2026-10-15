"""Blueprint de autenticación y páginas personales.

Registra rutas para solicitar el alta, entrar y cerrar sesión.
"""

from flask import Blueprint


bp = Blueprint("auth", __name__, url_prefix="/auth")

from app.blueprints.auth import routes  # noqa: E402,F401
