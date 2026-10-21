"""Modelos de cuotas de socios y movimientos económicos.

Conservan los importes como Decimal y validan los datos antes de guardarlos.
"""

import re
from decimal import Decimal

from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.orm import validates

from app.extensiones import db


class Cuota(db.Model):
    """Representa una cuota anual de una persona socia."""

    __table_args__ = (
        UniqueConstraint(
            "usuario_id",
            "periodo",
            name="uq_cuota_usuario_periodo",
        ),
        CheckConstraint("importe > 0", name="ck_cuota_importe_positivo"),
    )

    ESTADOS = ("pendiente", "pagada", "anulada")
    _FORMATO_RECIBO = re.compile(r"^R-\d{4}-\d{4}$")

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuario.id"),
        nullable=False,
    )
    usuario = db.relationship("Usuario", backref="cuotas")
    periodo = db.Column(db.Integer, nullable=False)
    importe = db.Column(db.Numeric(10, 2), nullable=False)
    estado = db.Column(db.String(20), nullable=False, default="pendiente")
    fecha_pago = db.Column(db.Date, nullable=True)
    numero_recibo = db.Column(db.String(11), unique=True, nullable=True)

    @validates("estado")
    def validar_estado(self, clave, valor):
        if valor not in self.ESTADOS:
            raise ValueError(f"Estado de cuota no permitido: {valor}")
        return valor

    @validates("importe")
    def validar_importe(self, clave, valor):
        if not isinstance(valor, Decimal):
            raise TypeError("El importe debe ser un valor Decimal.")
        if valor <= Decimal("0"):
            raise ValueError("El importe debe ser mayor que cero.")
        return valor

    @validates("numero_recibo")
    def validar_numero_recibo(self, clave, valor):
        if valor is not None and not self._FORMATO_RECIBO.fullmatch(valor):
            raise ValueError("El número de recibo debe tener el formato R-AAAA-NNNN.")
        return valor


class Movimiento(db.Model):
    """Registra un ingreso o gasto de la asociación."""

    __table_args__ = (
        CheckConstraint(
            "importe > 0",
            name="ck_movimiento_importe_positivo",
        ),
    )

    TIPOS = ("ingreso", "gasto")

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=False)
    concepto = db.Column(db.String(200), nullable=False)
    importe = db.Column(db.Numeric(10, 2), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    categoria = db.Column(db.String(100), nullable=True)

    @validates("tipo")
    def validar_tipo(self, clave, valor):
        if valor not in self.TIPOS:
            raise ValueError(f"Tipo de movimiento no permitido: {valor}")
        return valor

    @validates("importe")
    def validar_importe(self, clave, valor):
        if not isinstance(valor, Decimal):
            raise TypeError("El importe debe ser un valor Decimal.")
        if valor <= Decimal("0"):
            raise ValueError("El importe debe ser mayor que cero.")
        return valor
