"""Blueprint para consultar y administrar convocatorias de Asamblea.

La consulta requiere sesión y las modificaciones están reservadas a Junta.
"""

from flask import Blueprint


bp = Blueprint("asambleas", __name__, url_prefix="/asambleas")

from app.asambleas import rutas  # noqa: E402,F401
