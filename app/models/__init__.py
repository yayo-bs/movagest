"""Modelos de datos registrados en la aplicación.

Su importación permite que SQLAlchemy conozca todas las tablas del proyecto.
"""

from app.models.noticia import Noticia
from app.models.usuario import Usuario

__all__ = ["Noticia", "Usuario"]
