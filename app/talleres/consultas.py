"""Filtros compartidos para consultar talleres.

Centraliza la comprobación SQL del aforo disponible.
"""

from app.extensiones import db
from app.models import Inscripcion, Taller


def filtro_talleres_con_plazas_libres():
    inscripciones = (
        db.select(db.func.count(Inscripcion.id))
        .where(Inscripcion.taller_id == Taller.id)
        .scalar_subquery()
    )
    return inscripciones < Taller.plazas
