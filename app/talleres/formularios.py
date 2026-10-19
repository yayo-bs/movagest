"""Formularios para crear y editar talleres.

Validan los datos de actividad antes de guardarlos en la base de datos.
"""

from datetime import datetime

from flask_wtf import FlaskForm
from wtforms import DateTimeLocalField, IntegerField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, InputRequired, Length, NumberRange


class FormularioTaller(FlaskForm):
    titulo = StringField(
        "Título",
        validators=[DataRequired(), Length(max=200)],
    )
    descripcion = TextAreaField("Descripción", validators=[DataRequired()])
    fecha_hora = DateTimeLocalField(
        "Fecha y hora",
        format="%Y-%m-%dT%H:%M",
        validators=[DataRequired()],
        default=datetime.now,
    )
    lugar = StringField(
        "Lugar",
        validators=[DataRequired(), Length(max=200)],
    )
    plazas = IntegerField(
        "Plazas",
        validators=[
            InputRequired(),
            NumberRange(min=1, message="Debe haber al menos una plaza."),
        ],
    )
    guardar = SubmitField("Guardar taller")
