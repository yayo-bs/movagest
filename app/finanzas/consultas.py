"""Consultas auxiliares para los listados de cuotas.

Construye las opciones de periodo disponibles para filtrar los resultados.
"""

from app.extensiones import db
from app.models import Cuota


def periodos_de_cuotas():
    """Devuelve los periodos existentes ordenados del más reciente."""
    return db.session.scalars(
        db.select(Cuota.periodo).distinct().order_by(Cuota.periodo.desc())
    ).all()
