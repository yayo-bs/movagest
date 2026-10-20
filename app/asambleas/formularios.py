"""Formulario para crear o editar una convocatoria de Asamblea.

Comprueba los campos obligatorios y evita nuevas convocatorias en el pasado.
"""

from datetime import date

from flask_wtf import FlaskForm
from wtforms import DateTimeLocalField, SelectField, StringField, SubmitField
from wtforms import TextAreaField
from wtforms.validators import DataRequired, Length, ValidationError


class FormularioAsamblea(FlaskForm):
    """Valida los datos introducidos para una convocatoria."""

    def __init__(self, *args, permitir_fecha_pasada=False, **kwargs):
        self.permitir_fecha_pasada = permitir_fecha_pasada
        super().__init__(*args, **kwargs)

    titulo = StringField(
        "Título",
        validators=[DataRequired(), Length(max=200)],
    )
    tipo = SelectField(
        "Tipo",
        choices=[
            ("ordinaria", "Ordinaria"),
            ("extraordinaria", "Extraordinaria"),
        ],
        validators=[DataRequired()],
    )
    fecha_hora = DateTimeLocalField(
        "Fecha y hora",
        format="%Y-%m-%dT%H:%M",
        validators=[DataRequired()],
    )
    lugar = StringField(
        "Lugar (escribe «Por determinar» si aún no se conoce)",
        validators=[DataRequired(), Length(max=200)],
    )
    orden_del_dia = TextAreaField(
        "Orden del día",
        validators=[DataRequired()],
    )
    guardar = SubmitField("Guardar convocatoria")

    def validate_fecha_hora(self, campo):
        """No permite convocatorias pasadas al crear, pero sí al editar."""
        if (
            not self.permitir_fecha_pasada
            and campo.data is not None
            and campo.data.date() < date.today()
        ):
            raise ValidationError("La fecha no puede ser anterior a hoy.")
