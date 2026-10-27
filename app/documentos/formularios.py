"""Formulario de subida de documentos y actas.

Valida los campos y limita los archivos a extensiones permitidas.
"""

from flask import current_app
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from werkzeug.utils import secure_filename
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import (
    AnyOf,
    DataRequired,
    Length,
    Optional,
    ValidationError,
)


def validar_nombre_y_extension(formulario, campo):
    nombre_seguro = secure_filename(campo.data.filename or "")
    if not nombre_seguro:
        raise ValidationError("El nombre del archivo no es válido.")

    if "." not in nombre_seguro:
        raise ValidationError("El tipo de archivo no está permitido.")

    extension = nombre_seguro.rsplit(".", 1)[1].lower()
    if extension not in current_app.config["EXTENSIONES_DOCUMENTOS_PERMITIDAS"]:
        raise ValidationError("El tipo de archivo no está permitido.")


class FormularioDocumento(FlaskForm):
    titulo = StringField(
        "Título",
        validators=[DataRequired(), Length(max=200)],
    )
    descripcion = TextAreaField("Descripción", validators=[Optional()])
    categoria = SelectField(
        "Categoría",
        choices=[("documento", "Documento"), ("acta", "Acta")],
        validators=[
            DataRequired(),
            AnyOf(("documento", "acta"), message="Selecciona una categoría válida."),
        ],
    )
    archivo = FileField("Archivo")
    guardar = SubmitField("Subir archivo")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.archivo.validators = [
            FileRequired("Selecciona un archivo."),
            validar_nombre_y_extension,
            FileAllowed(
                current_app.config["EXTENSIONES_DOCUMENTOS_PERMITIDAS"],
                "El tipo de archivo no está permitido.",
            ),
        ]
