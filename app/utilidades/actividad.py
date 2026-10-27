"""Funciones para guardar el historial de acciones de MovaGest.

El registro usa un punto de guardado para aislar sus fallos de la acción principal.
"""

from flask import current_app, has_request_context
from flask_login import current_user

from app.extensiones import db
from app.models import Actividad


def registrar(accion, descripcion, usuario=None, commit=False):
    """Añade actividad; en un comando CLI aislado se puede usar `commit=True`.

    Ejemplo: `registrar("sistema.tarea", "Tarea completada", commit=True)`.
    """
    if usuario is None and has_request_context() and current_user.is_authenticated:
        usuario = current_user

    nombre = "Sistema"
    if usuario is not None:
        partes_nombre = [usuario.nombre, usuario.apellidos]
        nombre = " ".join(parte for parte in partes_nombre if parte).strip()
        if not nombre:
            nombre = "Sistema"

    try:
        with db.session.begin_nested():
            db.session.add(
                Actividad(
                    usuario=usuario,
                    usuario_nombre=nombre,
                    accion=accion,
                    descripcion=descripcion,
                )
            )
            db.session.flush()
        if commit:
            db.session.commit()
    except Exception:
        if commit and db.session.in_transaction():
            db.session.rollback()
        current_app.logger.warning(
            "No se pudo registrar la actividad %s.", accion, exc_info=True
        )
