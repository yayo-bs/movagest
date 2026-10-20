"""Filtros compartidos para consultar convocatorias de Asamblea.

Mantiene uniforme el límite temporal de las próximas convocatorias.
"""

from datetime import datetime, timezone

from app.models import Asamblea


def filtro_asambleas_futuras(incluir_momento_actual=False):
    ahora = datetime.now(timezone.utc).replace(tzinfo=None)
    if incluir_momento_actual:
        return Asamblea.fecha_hora >= ahora
    return Asamblea.fecha_hora > ahora
