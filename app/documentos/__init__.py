"""Blueprint para consultar y administrar documentos y actas.

Separa las rutas de archivos de noticias y otros módulos de la asociación.
"""

from flask import Blueprint, flash, render_template

bp = Blueprint("documentos", __name__, url_prefix="/documentos")


@bp.app_errorhandler(413)
def archivo_demasiado_grande(error):
    flash("El archivo supera el tamaño máximo permitido de 10 MB.", "error")
    return render_template("documentos/formulario.html", formulario=None), 413


from app.documentos import rutas  # noqa: E402,F401
