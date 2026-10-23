"""Rutas para talleres e inscripciones.

Los socios gestionan sus inscripciones y los administradores los talleres.
"""

from datetime import datetime, timezone

from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from app.decoradores import solo_administradores
from app.extensiones import db
from app.models import Inscripcion, Taller
from app.talleres import bp
from app.talleres.consultas import filtro_talleres_con_plazas_libres
from app.talleres.formularios import FormularioTaller
from app.utilidades.listados import paginar_consulta, preparar_listado


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


def _procesar_inscripcion(taller, usuario):
    if taller.esta_inscrito(usuario):
        return "Ya estás inscrito en este taller.", "warning"
    if _taller_ha_pasado(taller):
        return "Este taller ya ha finalizado y no admite inscripciones.", "warning"
    if taller.esta_completo:
        return "El taller está completo y no quedan plazas libres.", "warning"

    db.session.add(Inscripcion(taller=taller, usuario=usuario))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        inscripcion_existente = db.session.scalar(
            db.select(Inscripcion).where(
                Inscripcion.taller_id == taller.id,
                Inscripcion.usuario_id == usuario.id,
            )
        )
        if inscripcion_existente is None:
            raise
        return "Ya estás inscrito en este taller.", "warning"

    return "Te has inscrito correctamente en el taller.", "success"


@bp.get("/")
@login_required
def listar_talleres():
    consulta, valores = preparar_listado(
        db.select(Taller),
        request.args,
        [Taller.titulo, Taller.descripcion],
        {
            "fecha": Taller.fecha_hora,
            "titulo": Taller.titulo,
        },
        Taller.fecha_hora.asc(),
        filtros={
            "plazas_libres": {
                "si": filtro_talleres_con_plazas_libres(),
            }
        },
        direccion_por_defecto="asc",
    )
    paginacion = paginar_consulta(
        consulta,
        request.args.get("pagina"),
        current_app.config["POR_PAGINA"],
    )
    return render_template(
        "talleres/lista.html",
        talleres=paginacion.items,
        paginacion=paginacion,
        valores=valores,
        parametros_paginacion=valores,
        hay_filtros=bool(valores["q"] or valores["plazas_libres"]),
    )


@bp.get("/<int:id_taller>")
@login_required
def ver_taller(id_taller):
    taller = db.get_or_404(Taller, id_taller)
    return render_template("talleres/detalle.html", taller=taller)


@bp.post("/<int:id_taller>/inscribirse")
@login_required
def inscribirse(id_taller):
    taller = db.get_or_404(Taller, id_taller)
    mensaje, categoria = _procesar_inscripcion(taller, current_user)
    flash(mensaje, categoria)

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
        flash("Confirma que deseas eliminar este taller.", "warning")
        return redirect(url_for("talleres.ver_taller", id_taller=taller.id))
    db.session.delete(taller)
    db.session.commit()
    flash("El taller se ha eliminado correctamente.", "success")
    return redirect(url_for("talleres.listar_talleres"))
