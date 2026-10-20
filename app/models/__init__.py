"""Modelos de datos registrados en la aplicación.

Su importación permite que SQLAlchemy conozca todas las tablas del proyecto.
"""

from app.models.noticia import Noticia
from app.models.asamblea import Asamblea
from app.models.documento import Documento
from app.models.usuario import Usuario
from app.models.taller import Inscripcion, Taller

__all__ = [
    "Asamblea",
    "Documento",
    "Inscripcion",
    "Noticia",
    "Taller",
    "Usuario",
]
