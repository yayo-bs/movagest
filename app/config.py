"""Configuraciones de ejecución para desarrollo y pruebas.

Los valores sensibles y la conexión de desarrollo se leen del entorno.
"""

import os


class ConfiguracionBase:
    SECRET_KEY = os.getenv("SECRET_KEY", "clave-insegura-solo-desarrollo")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite:///movagest.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    POR_PAGINA = 10
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
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
    DEBUG = True


class ConfiguracionPruebas(ConfiguracionBase):
    TESTING = True
    SECRET_KEY = "clave-de-pruebas"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


CONFIGURACIONES = {
    "desarrollo": ConfiguracionDesarrollo,
    "testing": ConfiguracionPruebas,
}
