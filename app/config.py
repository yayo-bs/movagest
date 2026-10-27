"""Configuraciones de ejecución para los distintos entornos.

Los valores que dependen del despliegue se aplican al crear la aplicación.
"""

import os


class ConfiguracionBase:
    SECRET_KEY = None
    DEBUG = False
    MODO_PRODUCCION = False
    NOMBRE_ASOCIACION = "MovaGest"
    SQLALCHEMY_DATABASE_URI = "sqlite:///movagest.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    POR_PAGINA = 10
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    CARPETA_SUBIDAS = None
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    EXTENSIONES_DOCUMENTOS_PERMITIDAS = (
        "pdf",
        "doc",
        "docx",
        "odt",
        "jpg",
        "jpeg",
        "png",
    )


class ConfiguracionDesarrollo(ConfiguracionBase):
    MODO_DESARROLLO = True
    SECRET_KEY = "clave-local-solo-para-desarrollo"


class ConfiguracionPruebas(ConfiguracionBase):
    TESTING = True
    SECRET_KEY = "clave-de-pruebas"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


class ConfiguracionProduccion(ConfiguracionBase):
    MODO_PRODUCCION = True


CONFIGURACIONES = {
    "desarrollo": ConfiguracionDesarrollo,
    "testing": ConfiguracionPruebas,
    "produccion": ConfiguracionProduccion,
}


def aplicar_variables_entorno(configuracion):
    """Aplica variables de despliegue y valida sus valores."""
    clave = os.getenv("SECRET_KEY")
    if clave and clave.strip() and not configuracion.get("TESTING"):
        configuracion["SECRET_KEY"] = clave

    configuracion["DEBUG"] = os.getenv("FLASK_DEBUG", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    configuracion["NOMBRE_ASOCIACION"] = os.getenv(
        "NOMBRE_ASOCIACION",
        configuracion["NOMBRE_ASOCIACION"],
    )

    if not configuracion.get("TESTING"):
        configuracion["SQLALCHEMY_DATABASE_URI"] = os.getenv(
            "DATABASE_URL",
            configuracion["SQLALCHEMY_DATABASE_URI"],
        )

    carpeta_subidas = os.getenv("CARPETA_SUBIDAS")
    if carpeta_subidas:
        configuracion["CARPETA_SUBIDAS"] = carpeta_subidas

    maximo = os.getenv("MAX_CONTENT_LENGTH")
    if maximo:
        try:
            configuracion["MAX_CONTENT_LENGTH"] = int(maximo)
        except ValueError as error:
            raise RuntimeError(
                "MAX_CONTENT_LENGTH debe ser un número entero de bytes."
            ) from error
        if configuracion["MAX_CONTENT_LENGTH"] <= 0:
            raise RuntimeError("MAX_CONTENT_LENGTH debe ser mayor que cero.")

    seguro = os.getenv("SESSION_COOKIE_SECURE", "").strip().lower()
    configuracion["SESSION_COOKIE_SECURE"] = seguro in {
        "1",
        "true",
        "yes",
        "on",
    }
    configuracion["SESSION_COOKIE_HTTPONLY"] = True
    configuracion["SESSION_COOKIE_SAMESITE"] = "Lax"
