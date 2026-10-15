"""Formularios para solicitar un alta y acceder a una cuenta.

Flask-WTF valida los campos y protege los envíos con CSRF.
"""

from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length


class FormularioRegistro(FlaskForm):
    nombre = StringField("Nombre", validators=[DataRequired(), Length(max=100)])
    apellidos = StringField(
        "Apellidos", validators=[DataRequired(), Length(max=150)]
    )
    email = StringField("Correo electrónico", validators=[DataRequired()])
    password = PasswordField(
        "Contraseña", validators=[DataRequired(), Length(min=8)]
    )
    repetir_password = PasswordField(
        "Repetir contraseña",
        validators=[
            DataRequired(),
            EqualTo("password", message="Las contraseñas deben coincidir."),
        ],
    )
    enviar = SubmitField("Enviar solicitud")


class FormularioLogin(FlaskForm):
    email = StringField("Correo electrónico", validators=[DataRequired()])
    password = PasswordField("Contraseña", validators=[DataRequired()])
    enviar = SubmitField("Entrar")
