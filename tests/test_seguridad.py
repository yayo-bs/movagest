"""Pruebas de configuración segura y validación de archivos subidos.

Usan la base de datos en memoria y el directorio temporal de las fixtures.
"""

from io import BytesIO
import os

import pytest

from app import create_app
from app.extensiones import db
from app.models import Documento
from tests.conftest import iniciar_sesion


def _datos_archivo(nombre, contenido):
    return {
        "titulo": "Archivo de prueba",
        "descripcion": "",
        "categoria": "documento",
        "archivo": (BytesIO(contenido), nombre),
    }


def _crear_administrador(crear_usuario):
    return crear_usuario(
        email="admin-seguridad@example.com",
        rol="administrador",
        estado="activo",
    )


def test_produccion_sin_secret_key_falla_con_mensaje_claro(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="Falta SECRET_KEY"):
        create_app("produccion")


def test_debug_desactivado_por_defecto(monkeypatch):
    monkeypatch.delenv("FLASK_DEBUG", raising=False)

    aplicacion = create_app("desarrollo")

    assert aplicacion.config["DEBUG"] is False


def test_cookies_de_sesion_tienen_atributos_seguros(
    app, cliente, crear_usuario
):
    administrador = _crear_administrador(crear_usuario)
    respuesta = cliente.post(
        "/auth/login",
        data={
            "email": administrador.email,
            "password": "clave-segura-123",
        },
    )

    assert respuesta.status_code == 302
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert "HttpOnly" in respuesta.headers["Set-Cookie"]
    assert "SameSite=Lax" in respuesta.headers["Set-Cookie"]


def test_subida_con_extension_doble_se_rechaza(
    app, cliente, crear_usuario
):
    administrador = _crear_administrador(crear_usuario)
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.post(
        "/documentos/nuevo",
        data=_datos_archivo("informe.pdf.exe", b"%PDF-1.4\n"),
        content_type="multipart/form-data",
    )

    assert respuesta.status_code == 200
    assert b"El tipo de archivo no est\xc3\xa1 permitido." in respuesta.data
    assert db.session.scalar(db.select(Documento)) is None


def test_nombre_vacio_tras_secure_filename_se_rechaza(
    app, cliente, crear_usuario
):
    administrador = _crear_administrador(crear_usuario)
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.post(
        "/documentos/nuevo",
        data=_datos_archivo("...", b"%PDF-1.4\n"),
        content_type="multipart/form-data",
    )

    assert respuesta.status_code == 200
    assert b"El nombre del archivo no es v\xc3\xa1lido." in respuesta.data
    assert db.session.scalar(db.select(Documento)) is None


def test_extension_permitida_con_firma_incorrecta_se_rechaza(
    app, cliente, crear_usuario
):
    administrador = _crear_administrador(crear_usuario)
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.post(
        "/documentos/nuevo",
        data=_datos_archivo("informe.PDF", b"no es un PDF"),
        content_type="multipart/form-data",
    )

    assert respuesta.status_code == 200
    assert b"El contenido no coincide" in respuesta.data
    assert db.session.scalar(db.select(Documento)) is None


def test_archivo_guardado_usa_nombre_generado(
    app, cliente, crear_usuario
):
    administrador = _crear_administrador(crear_usuario)
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.post(
        "/documentos/nuevo",
        data=_datos_archivo("informe original.pdf", b"%PDF-1.4\ncontenido"),
        content_type="multipart/form-data",
    )
    documento = db.session.scalar(db.select(Documento))

    assert respuesta.status_code == 302
    assert documento.nombre_original == "informe original.pdf"
    assert documento.nombre_archivo != documento.nombre_original
    assert documento.nombre_archivo.endswith(".pdf")
    assert os.path.isfile(
        os.path.join(app.config["CARPETA_SUBIDAS"], documento.nombre_archivo)
    )


def test_solicitud_mayor_al_limite_muestra_error_413(
    app, cliente, crear_usuario
):
    administrador = _crear_administrador(crear_usuario)
    iniciar_sesion(cliente, administrador)
    app.config["MAX_CONTENT_LENGTH"] = 64

    respuesta = cliente.post(
        "/documentos/nuevo",
        data=_datos_archivo("informe.pdf", b"%PDF-1.4\n" + b"x" * 100),
        content_type="multipart/form-data",
    )

    assert respuesta.status_code == 413
    assert b"Archivo demasiado grande" in respuesta.data
    assert b"errores/413" not in respuesta.data
    assert b"64 bytes" in respuesta.data


def test_descarga_sin_login_redirige_al_login(cliente):
    respuesta = cliente.get("/documentos/1/descargar")

    assert respuesta.status_code == 302
    assert respuesta.headers["Location"].startswith("/auth/login?next=")


def test_carpeta_de_subidas_esta_fuera_de_static(app):
    carpeta_subidas = os.path.realpath(app.config["CARPETA_SUBIDAS"])
    carpeta_static = os.path.realpath(app.static_folder)

    assert os.path.commonpath([carpeta_subidas, carpeta_static]) != carpeta_static
