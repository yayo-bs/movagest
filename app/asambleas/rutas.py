"""Rutas para consultar y administrar convocatorias de Asamblea.

Socios y administradores consultan; solo administración puede modificarlas.
"""

from datetime import timezone

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.asambleas import bp
from app.asambleas.formularios import FormularioAsamblea
from app.decoradores import solo_administradores
from app.extensiones import db
from app.models import Asamblea


def _guardar_asamblea(asamblea, formulario):
    """Copia al modelo los campos validados del formulario."""
    asamblea.titulo = formulario.titulo.data.strip()
    asamblea.tipo = formulario.tipo.data
    asamblea.fecha_hora = formulario.fecha_hora.data.replace(
        tzinfo=timezone.utc
    )
    asamblea.lugar = formulario.lugar.data.strip()
    asamblea.orden_del_dia = formulario.orden_del_dia.data.strip()


@bp.get("/")
@login_required
def listar_asambleas():
    asambleas = db.session.scalars(
        db.select(Asamblea).order_by(Asamblea.fecha_hora.asc())
    ).all()
    futuras = [asamblea for asamblea in asambleas if asamblea.es_futura]
    pasadas = [asamblea for asamblea in asambleas if not asamblea.es_futura]
    pasadas.reverse()
    return render_template(
        "asambleas/listado.html",
        futuras=futuras,
        pasadas=pasadas,
    )


@bp.get("/<int:id_asamblea>")
@login_required
def ver_asamblea(id_asamblea):
    asamblea = db.get_or_404(Asamblea, id_asamblea)
    return render_template("asambleas/detalle.html", asamblea=asamblea)


@bp.route("/nueva", methods=["GET", "POST"])
@solo_administradores
def nueva_asamblea():
    formulario = FormularioAsamblea()
    if formulario.validate_on_submit():
        asamblea = Asamblea(autor=current_user)
        _guardar_asamblea(asamblea, formulario)
        db.session.add(asamblea)
        db.session.commit()
        flash("La convocatoria se ha creado correctamente.", "success")
        return redirect(url_for("asambleas.ver_asamblea", id_asamblea=asamblea.id))
    return render_template(
        "asambleas/formulario.html",
        formulario=formulario,
    )


@bp.route("/<int:id_asamblea>/editar", methods=["GET", "POST"])
@solo_administradores
def editar_asamblea(id_asamblea):
    asamblea = db.get_or_404(Asamblea, id_asamblea)
    formulario = FormularioAsamblea(
        obj=asamblea,
        permitir_fecha_pasada=True,
    )
    if formulario.validate_on_submit():
        _guardar_asamblea(asamblea, formulario)
        db.session.commit()
        flash("La convocatoria se ha actualizado correctamente.", "success")
        return redirect(url_for("asambleas.ver_asamblea", id_asamblea=asamblea.id))
    return render_template(
        "asambleas/formulario.html",
        formulario=formulario,
        asamblea=asamblea,
    )


@bp.post("/<int:id_asamblea>/eliminar")
@solo_administradores
def eliminar_asamblea(id_asamblea):
    asamblea = db.get_or_404(Asamblea, id_asamblea)
    if request.form.get("confirmar_eliminacion") != "si":
        flash("Confirma que deseas eliminar esta convocatoria.", "warning")
        return redirect(
            url_for("asambleas.ver_asamblea", id_asamblea=asamblea.id)
        )
    db.session.delete(asamblea)
    db.session.commit()
    flash("La convocatoria se ha eliminado correctamente.", "success")
    return redirect(url_for("asambleas.listar_asambleas"))
