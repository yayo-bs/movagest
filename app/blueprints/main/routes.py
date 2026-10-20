"""Rutas generales de MovaGest.

Mantiene la portada pública y el inicio de las cuentas autenticadas.
"""

from flask import render_template
from flask_login import current_user, login_required

from app.blueprints.main import bp
from app.blueprints.main.consultas import (
    contar_altas_pendientes,
    obtener_inscripciones_futuras,
    obtener_proxima_asamblea,
    obtener_talleres_disponibles,
    obtener_ultimas_noticias,
    obtener_ultimos_documentos,
)


@bp.get("/")
def home_publica():
    return render_template("home.html")


@bp.get("/inicio")
@login_required
def inicio():
    datos = {
        "usuario": current_user,
        "noticias": obtener_ultimas_noticias(),
        "asamblea": obtener_proxima_asamblea(),
        "talleres": obtener_talleres_disponibles(),
        "inscripciones": obtener_inscripciones_futuras(current_user.id),
        "documentos": obtener_ultimos_documentos(),
    }
    if current_user.es_administrador():
        datos["solicitudes_pendientes"] = contar_altas_pendientes()

    return render_template("main/inicio.html", **datos)
