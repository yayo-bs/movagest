from flask import render_template

from app.blueprints.main import bp


@bp.get("/")
def inicio():
    """Muestra la página de inicio."""
    return render_template("home.html")
