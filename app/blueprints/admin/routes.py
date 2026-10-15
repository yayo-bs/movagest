"""Rutas administrativas para revisar solicitudes de alta.

Las acciones de aprobación y rechazo se delegan al modelo Usuario.
"""

from flask import abort, flash, redirect, render_template, url_for

from app.blueprints.admin import bp
from app.decoradores import solo_administradores
from app.extensiones import db
from app.models import Usuario


@bp.get("/altas")
@solo_administradores
def listar_altas():
    usuarios = db.session.scalars(
        db.select(Usuario)
        .where(Usuario.estado == "pendiente")
        .order_by(Usuario.fecha_alta)
    ).all()
    return render_template("admin/altas.html", usuarios=usuarios)


@bp.post("/altas/<int:id_usuario>/aprobar")
@solo_administradores
def aprobar_alta(id_usuario):
    usuario = db.session.get(Usuario, id_usuario)
    if usuario is None:
        abort(404)
    if not usuario.aprobar():
        flash("La solicitud ya no está pendiente.", "warning")
        return redirect(url_for("admin.listar_altas"))

    db.session.commit()
    flash(f"Se ha aprobado el alta de {usuario.nombre}.", "success")
    return redirect(url_for("admin.listar_altas"))


@bp.post("/altas/<int:id_usuario>/rechazar")
@solo_administradores
def rechazar_alta(id_usuario):
    usuario = db.session.get(Usuario, id_usuario)
    if usuario is None:
        abort(404)
    if not usuario.rechazar():
        flash("La solicitud ya no está pendiente.", "warning")
        return redirect(url_for("admin.listar_altas"))

    db.session.commit()
    flash(f"Se ha rechazado el alta de {usuario.nombre}.", "success")
    return redirect(url_for("admin.listar_altas"))
