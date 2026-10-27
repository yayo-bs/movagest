"""Comandos CLI para preparar MovaGest en un entorno local.

Incluye tablas de desarrollo y la cuenta administradora inicial.
"""

import click
from flask.cli import with_appcontext
from sqlalchemy.exc import IntegrityError

from app.extensiones import db
from app.models import Usuario
from app.demo import comando_cargar_demo


@click.command("init-db")
@with_appcontext
def inicializar_base_datos():
    """Crea las tablas que todavía no existen sin borrar datos."""
    db.create_all()
    click.echo("Base de datos inicializada correctamente.")


@click.command("crear-admin")
@with_appcontext
def crear_administrador():
    """Solicita los datos y crea la primera cuenta administradora."""
    nombre = click.prompt("Nombre")
    apellidos = click.prompt("Apellidos")
    email = click.prompt("Correo electrónico").strip().lower()

    usuario_existente = db.session.scalar(
        db.select(Usuario).where(Usuario.email == email)
    )
    if usuario_existente is not None:
        click.echo("Ya existe un usuario con ese correo electrónico.")
        return

    password = click.prompt(
        "Contraseña", hide_input=True, confirmation_prompt=True
    )
    usuario = Usuario(
        nombre=nombre.strip(),
        apellidos=apellidos.strip(),
        email=email,
        rol="administrador",
        estado="activo",
    )
    usuario.establecer_password(password)
    db.session.add(usuario)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        usuario_existente = db.session.scalar(
            db.select(Usuario).where(Usuario.email == email)
        )
        if usuario_existente is None:
            raise
        click.echo("Ya existe un usuario con ese correo electrónico.")
        return

    click.echo(f"Administrador creado: {usuario.email}")


def registrar_comandos(app):
    """Registra los comandos propios en la aplicación Flask."""
    app.cli.add_command(inicializar_base_datos)
    app.cli.add_command(crear_administrador)
    app.cli.add_command(comando_cargar_demo)
