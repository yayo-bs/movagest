"""Blueprint de las funciones financieras de MovaGest.

Agrupa las rutas de cuotas, movimientos y recibos.
"""

from flask import Blueprint


bp = Blueprint("finanzas", __name__, url_prefix="/finanzas")
