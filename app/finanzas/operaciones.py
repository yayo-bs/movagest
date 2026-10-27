"""Operaciones compartidas para generar y cambiar el estado de cuotas.

Centraliza la asignación de recibos para que las rutas y los comandos sigan
las mismas reglas financieras.
"""

from datetime import date

from app.extensiones import db
from app.models import Cuota, Usuario
from app.utilidades.actividad import registrar


def generar_cuotas(periodo, importe, socios=None, usuario=None, marca=""):
    """Crea una cuota pendiente para cada socio indicado que no la tenga."""
    if socios is None:
        socios = db.session.scalars(
            db.select(Usuario).where(
                Usuario.rol == "socio",
                Usuario.estado == "activo",
            )
        ).all()

    ids_con_cuota = set(
        db.session.scalars(
            db.select(Cuota.usuario_id).where(Cuota.periodo == periodo)
        ).all()
    )
    cuotas_nuevas = [
        Cuota(
            usuario=socio,
            periodo=periodo,
            importe=importe,
            estado="pendiente",
        )
        for socio in socios
        if socio.id not in ids_con_cuota
    ]
    db.session.add_all(cuotas_nuevas)
    registrar(
        "cuota.generar",
        f"{marca}Generadas {len(cuotas_nuevas)} cuotas para el periodo {periodo}",
        usuario=usuario,
    )
    return len(cuotas_nuevas)


def numero_recibo_siguiente(anio):
    """Calcula el siguiente número correlativo de recibo de ese año."""
    ultimo_numero = db.session.scalar(
        db.select(db.func.max(Cuota.numero_recibo)).where(
            Cuota.numero_recibo.like(f"R-{anio}-%")
        )
    )
    if ultimo_numero is None:
        return 1
    return int(ultimo_numero[-4:]) + 1


def marcar_cuota_pagada(cuota, fecha_pago, usuario=None, marca=""):
    """Marca como pagada una cuota pendiente y le asigna su recibo."""
    if cuota.estado != "pendiente":
        raise ValueError("Solo se puede pagar una cuota pendiente.")

    if cuota.numero_recibo is None:
        numero = numero_recibo_siguiente(fecha_pago.year)
        if numero > 9999:
            raise ValueError("No se pueden asignar más recibos para este año.")
        cuota.numero_recibo = f"R-{fecha_pago.year:04d}-{numero:04d}"

    cuota.fecha_pago = fecha_pago
    cuota.estado = "pagada"
    registrar(
        "cuota.pagar",
        f"{marca}Pagada la cuota {cuota.periodo} de {cuota.usuario.nombre} "
        f"{cuota.usuario.apellidos}".strip(),
        usuario=usuario,
    )


def anular_cuota(cuota, usuario=None, marca=""):
    """Anula una cuota pagada y conserva su número de recibo."""
    if cuota.estado != "pagada":
        raise ValueError("Solo se pueden anular cuotas pagadas.")

    cuota.estado = "anulada"
    registrar(
        "cuota.anular",
        f"{marca}Anulada la cuota {cuota.periodo} de {cuota.usuario.nombre} "
        f"{cuota.usuario.apellidos}".strip(),
        usuario=usuario,
    )
