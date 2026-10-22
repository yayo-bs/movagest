"""Consultas auxiliares para los listados financieros.

Obtiene los periodos existentes en cuotas y movimientos.
"""

from datetime import date

from app.extensiones import db
from app.models import Cuota, Movimiento


def periodos_de_cuotas():
    """Devuelve los periodos existentes ordenados del más reciente."""
    return db.session.scalars(
        db.select(Cuota.periodo).distinct().order_by(Cuota.periodo.desc())
    ).all()


def anios_resumen():
    """Incluye años con movimientos o cuotas pagadas, además del año actual."""
    fechas_movimientos = db.session.scalars(
        db.select(Movimiento.fecha).distinct()
    ).all()
    fechas_cuotas = db.session.scalars(
        db.select(Cuota.fecha_pago)
        .where(Cuota.estado == "pagada", Cuota.fecha_pago.is_not(None))
        .distinct()
    ).all()
    anios = {fecha.year for fecha in fechas_movimientos + fechas_cuotas}
    anios.add(date.today().year)
    return sorted(anios, reverse=True)


def obtener_cuotas_usuario(id_usuario):
    """Devuelve las cuotas de una persona, de periodo más reciente a antiguo."""
    return db.session.scalars(
        db.select(Cuota)
        .where(Cuota.usuario_id == id_usuario)
        .order_by(Cuota.periodo.desc())
    ).all()
