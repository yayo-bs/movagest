"""Decoradores de acceso para las vistas de MovaGest.

Protegen las rutas administrativas según la sesión y el rol del usuario.
"""

from functools import wraps

from flask import abort, redirect, request, url_for
from flask_login import current_user


def solo_administradores(funcion):
    """Permite la vista solo a usuarios con sesión y rol administrador."""

    @wraps(funcion)  # Conserva el nombre original de la vista en Flask.
    def vista_protegida(*args, **kwargs):  # Recibe los argumentos de la ruta.
        if not current_user.is_authenticated:  # Primero comprueba la sesión.
            return redirect(  # Envía a iniciar sesión y conserva la ruta deseada.
                url_for("auth.login", next=request.path)
            )
        if not current_user.es_administrador():  # Luego comprueba el rol.
            abort(403)  # Un usuario con sesión sin permisos recibe acceso denegado.
        return funcion(*args, **kwargs)  # Si pasa ambas comprobaciones, ejecuta la vista.

    return vista_protegida  # Flask registra la versión protegida de la vista.
