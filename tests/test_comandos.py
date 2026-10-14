"""Pruebas de los comandos CLI de MovaGest.

Comprueban la inicialización de tablas y la creación del primer administrador.
"""

from sqlalchemy import inspect

from app.extensiones import db
from app.models import Usuario


def test_init_db_crea_tablas_y_se_puede_repetir(app):
    runner = app.test_cli_runner()

    primera_ejecucion = runner.invoke(args=["init-db"])
    segunda_ejecucion = runner.invoke(args=["init-db"])

    assert primera_ejecucion.exit_code == 0
    assert "Base de datos inicializada correctamente." in primera_ejecucion.output
    assert segunda_ejecucion.exit_code == 0
    assert inspect(db.engine).has_table("usuario")


def test_crear_admin_crea_administrador_activo(app):
    runner = app.test_cli_runner()
    resultado = runner.invoke(
        args=["crear-admin"],
        input="Ana\nPérez\nADMIN@example.com\nclave-segura\nclave-segura\n",
    )

    usuario = db.session.scalar(
        db.select(Usuario).where(Usuario.email == "admin@example.com")
    )

    assert resultado.exit_code == 0
    assert "Administrador creado: admin@example.com" in resultado.output
    assert usuario.nombre == "Ana"
    assert usuario.apellidos == "Pérez"
    assert usuario.rol == "administrador"
    assert usuario.estado == "activo"
    assert usuario.comprobar_password("clave-segura")
    assert "clave-segura" not in resultado.output


def test_crear_admin_con_email_existente_no_duplica(app):
    existente = Usuario(
        nombre="Ana",
        apellidos="Pérez",
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    existente.establecer_password("clave-segura")
    db.session.add(existente)
    db.session.commit()

    resultado = app.test_cli_runner().invoke(
        args=["crear-admin"],
        input="Otra\nPersona\nADMIN@example.com\n",
    )

    administradores = db.session.scalars(
        db.select(Usuario).where(Usuario.email == "admin@example.com")
    ).all()

    assert resultado.exit_code == 0
    assert "Ya existe un usuario con ese correo electrónico." in resultado.output
    assert len(administradores) == 1
