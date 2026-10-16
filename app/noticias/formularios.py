"""Formulario para crear o editar una noticia.

Los campos obligatorios se validan en servidor mediante Flask-WTF.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length


class FormularioNoticia(FlaskForm):
    titulo = StringField(
        "Título",
        validators=[DataRequired(), Length(max=200)],
    )
    contenido = TextAreaField("Contenido", validators=[DataRequired()])
    guardar = SubmitField("Guardar noticia")
