"""Rutas públicas generales de MovaGest.

Incluye la página de inicio accesible sin autenticación.
"""

from flask import render_template

from app.blueprints.main import bp


@bp.get("/")
def inicio():
    return render_template("home.html")
