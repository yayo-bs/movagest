"""Rutas para solicitar el alta y gestionar la sesión de usuario.

Los usuarios nuevos permanecen pendientes hasta que administración decida.
"""

from urllib.parse import urlsplit

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError

from app.blueprints.auth import bp
from app.blueprints.auth.forms import FormularioLogin, FormularioRegistro
from app.extensiones import db
from app.models import Usuario


def _destino_interno(destino):
    """Acepta únicamente rutas relativas al mismo sitio."""
    if not destino or "\\" in destino or any(ord(caracter) < 32 for caracter in destino):
        return False

    partes = urlsplit(destino)
    return (
        destino.startswith("/")
        and not destino.startswith("//")
        and not partes.scheme
        and not partes.netloc
    )


@bp.route("/registro", methods=["GET", "POST"])
def registro():
    formulario = FormularioRegistro()
    if formulario.validate_on_submit():
        email = formulario.email.data.strip().lower()
        usuario_existente = db.session.scalar(
            db.select(Usuario).where(Usuario.email == email)
        )
        if usuario_existente:
            formulario.email.errors.append(
                "Ya existe una cuenta con este correo electrónico."
            )
            return render_template("auth/registro.html", formulario=formulario)

        usuario = Usuario(
            nombre=formulario.nombre.data.strip(),
            apellidos=formulario.apellidos.data.strip(),
            email=email,
        )
        usuario.establecer_password(formulario.password.data)
        db.session.add(usuario)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            formulario.email.errors.append(
                "Ya existe una cuenta con este correo electrónico."
            )
            return render_template("auth/registro.html", formulario=formulario)

        flash(
            "Solicitud enviada: un administrador debe aprobar tu alta.",
            "success",
        )
        return redirect(url_for("auth.login"))

    return render_template("auth/registro.html", formulario=formulario)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.inicio"))

    formulario = FormularioLogin()
    if formulario.validate_on_submit():
        email = formulario.email.data.strip().lower()
        usuario = db.session.scalar(
            db.select(Usuario).where(Usuario.email == email)
        )
        if usuario is None or not usuario.comprobar_password(
            formulario.password.data
        ):
            flash("Correo electrónico o contraseña incorrectos.", "error")
        elif usuario.estado == "pendiente":
            flash("Tu alta está pendiente de aprobación.", "warning")
        elif usuario.estado == "rechazado":
            flash("Tu solicitud de alta ha sido rechazada.", "error")
        elif usuario.estado == "baja":
            flash("Tu cuenta está de baja y no puedes iniciar sesión.", "error")
        else:
            login_user(usuario)
            destino = request.args.get("next")
            if _destino_interno(destino):
                return redirect(destino)
            return redirect(url_for("main.inicio"))

    return render_template("auth/login.html", formulario=formulario)


@bp.post("/logout")
def logout():
    logout_user()
    return redirect(url_for("main.inicio"))


@bp.get("/inicio")
@login_required
def inicio_socio():
    return render_template("auth/inicio.html", usuario=current_user)
