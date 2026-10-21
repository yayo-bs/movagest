"""Formularios administrativos para gestionar cuotas de socios.

Validan importes decimales, periodos y fechas de pago antes de guardar.
"""

from datetime import date, datetime
from decimal import Decimal

from flask_wtf import FlaskForm
from wtforms import DateField, DecimalField, IntegerField, SubmitField
from wtforms.validators import (
    InputRequired,
    NumberRange,
    ValidationError,
)

IMPORTE_MAXIMO = Decimal("99999999.99")


def validar_fecha_no_futura(formulario, campo):
    """Impide registrar un pago con una fecha posterior a hoy."""
    if campo.data and campo.data > date.today():
        raise ValidationError("La fecha de pago no puede ser futura.")


def validar_importe_positivo(formulario, campo):
    """Exige un Decimal finito y dentro del rango de Numeric(10, 2)."""
    if campo.data is None:
        return
    if (
        not campo.data.is_finite()
        or campo.data <= Decimal("0")
        or campo.data > IMPORTE_MAXIMO
    ):
        raise ValidationError(
            "El importe debe estar entre 0,01 y 99.999.999,99."
        )


class FormularioGenerarCuotas(FlaskForm):
    """Solicita el periodo y el importe de las nuevas cuotas."""

    periodo = IntegerField(
        "Periodo",
        validators=[
            InputRequired(),
            NumberRange(min=1, max=9999),
        ],
        default=lambda: datetime.now().year,
    )
    importe = DecimalField(
        "Importe",
        places=2,
        validators=[InputRequired(), validar_importe_positivo],
    )
    guardar = SubmitField("Generar cuotas")


class FormularioEditarCuota(FlaskForm):
    """Permite cambiar el importe de una cuota pendiente."""

    importe = DecimalField(
        "Importe",
        places=2,
        validators=[InputRequired(), validar_importe_positivo],
    )
    guardar = SubmitField("Guardar importe")


class FormularioPagoCuota(FlaskForm):
    """Solicita la fecha del pago antes de asignar el recibo."""

    fecha_pago = DateField(
        "Fecha de pago",
        validators=[InputRequired(), validar_fecha_no_futura],
        default=date.today,
    )
    guardar = SubmitField("Marcar como pagada")
