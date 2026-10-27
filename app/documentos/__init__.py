"""Blueprint para consultar y administrar documentos y actas.

Separa las rutas de archivos de noticias y otros módulos de la asociación.
"""

from flask import Blueprint

bp = Blueprint("documentos", __name__, url_prefix="/documentos")


from app.documentos import rutas  # noqa: E402,F401
