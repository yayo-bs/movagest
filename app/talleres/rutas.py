"""Rutas para talleres e inscripciones.

Los socios gestionan sus inscripciones y los administradores los talleres.
"""

from datetime import datetime, timezone

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from app.decoradores import solo_administradores
from app.extensiones import db
from app.models import Inscripcion, Taller
from app.talleres import bp
from app.talleres.formularios import FormularioTaller


def _fecha_con_zona(fecha):
    if fecha.tzinfo is None:
        return fecha.replace(tzinfo=timezone.utc)
    return fecha


def _taller_ha_pasado(taller):
    return _fecha_con_zona(taller.fecha_hora) < datetime.now(timezone.utc)


def _guardar_taller(taller, formulario):
    taller.titulo = formulario.titulo.data.strip()
    taller.descripcion = formulario.descripcion.data.strip()
    taller.fecha_hora = _fecha_con_zona(formulario.fecha_hora.data)
    taller.lugar = formulario.lugar.data.strip()
    taller.plazas = formulario.plazas.data


@bp.get("/")
@login_required
def listar_talleres():
    talleres = db.session.scalars(
        db.select(Taller).order_by(Taller.fecha_hora.asc())
    ).all()
    return render_template("talleres/lista.html", talleres=talleres)


@bp.get("/<int:id_taller>")
@login_required
def ver_taller(id_taller):
    taller = db.get_or_404(Taller, id_taller)
    return render_template("talleres/detalle.html", taller=taller)


@bp.post("/<int:id_taller>/inscribirse")
@login_required
def inscribirse(id_taller):
    taller = db.get_or_404(Taller, id_taller)
    if taller.esta_inscrito(current_user):
        flash("Ya estás inscrito en este taller.", "warning")
    elif _taller_ha_pasado(taller):
        flash("Este taller ya ha finalizado y no admite inscripciones.", "warning")
    elif taller.esta_completo:
        flash("El taller está completo y no quedan plazas libres.", "warning")
    else:
        db.session.add(
            Inscripcion(taller=taller, usuario=current_user)
        )
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            inscripcion_existente = db.session.scalar(
                db.select(Inscripcion).where(
                    Inscripcion.taller_id == id_taller,
                    Inscripcion.usuario_id == current_user.id,
                )
            )
            if inscripcion_existente is None:
                raise
            flash("Ya estás inscrito en este taller.", "warning")
        else:
            flash("Te has inscrito correctamente en el taller.", "success")

    return redirect(url_for("talleres.ver_taller", id_taller=id_taller))


@bp.post("/<int:id_taller>/cancelar")
@login_required
def cancelar_inscripcion(id_taller):
    taller = db.get_or_404(Taller, id_taller)
    inscripcion = db.session.scalar(
        db.select(Inscripcion).where(
            Inscripcion.taller_id == id_taller,
            Inscripcion.usuario_id == current_user.id,
        )
    )
    if inscripcion is None:
        flash("No tienes una inscripción que cancelar.", "warning")
    else:
        db.session.delete(inscripcion)
        db.session.commit()
        flash("Has cancelado tu inscripción.", "success")
    return redirect(url_for("talleres.ver_taller", id_taller=taller.id))


@bp.route("/nuevo", methods=["GET", "POST"])
@solo_administradores
def nuevo_taller():
    formulario = FormularioTaller()
    if formulario.validate_on_submit():
        taller = Taller(creado_por=current_user)
        _guardar_taller(taller, formulario)
        db.session.add(taller)
        db.session.commit()
        flash("El taller se ha creado correctamente.", "success")
        return redirect(url_for("talleres.ver_taller", id_taller=taller.id))
    return render_template("talleres/formulario.html", formulario=formulario)


@bp.route("/<int:id_taller>/editar", methods=["GET", "POST"])
@solo_administradores
def editar_taller(id_taller):
    taller = db.get_or_404(Taller, id_taller)
    formulario = FormularioTaller(obj=taller)
    if request.method == "POST":
        if (
            formulario.plazas.data is not None
            and formulario.plazas.data < taller.plazas_ocupadas
        ):
            formulario.plazas.errors = [
                "No puedes establecer menos plazas que las inscripciones actuales."
            ]
        elif formulario.validate():
            _guardar_taller(taller, formulario)
            db.session.commit()
            flash("El taller se ha actualizado correctamente.", "success")
            return redirect(
                url_for("talleres.ver_taller", id_taller=taller.id)
            )
    return render_template(
        "talleres/formulario.html",
        formulario=formulario,
        taller=taller,
    )


@bp.post("/<int:id_taller>/borrar")
@solo_administradores
def borrar_taller(id_taller):
    taller = db.get_or_404(Taller, id_taller)
    if request.form.get("confirmar_borrado") != "si":
        flash("Confirma que deseas borrar este taller.", "warning")
        return redirect(url_for("talleres.ver_taller", id_taller=taller.id))
    db.session.delete(taller)
    db.session.commit()
    flash("El taller se ha borrado correctamente.", "success")
    return redirect(url_for("talleres.listar_talleres"))
