"""Blueprint para consultar y administrar noticias.

Las noticias públicas requieren autenticación; su gestión es administrativa.
"""

from flask import Blueprint


bp = Blueprint("noticias", __name__, url_prefix="/noticias")

from app.noticias import rutas  # noqa: E402,F401
