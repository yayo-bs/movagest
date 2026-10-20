"""Rutas para consultar y administrar convocatorias de Asamblea.

Socios y administradores consultan; solo administración puede modificarlas.
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

from app.asambleas import bp
from app.asambleas.consultas import filtro_asambleas_futuras
from app.asambleas.formularios import FormularioAsamblea
from app.decoradores import solo_administradores
from app.extensiones import db
from app.models import Asamblea
from app.utilidades.listados import paginar_consulta, preparar_listado


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
    ahora = datetime.now(timezone.utc).replace(tzinfo=None)
    fecha_futura = filtro_asambleas_futuras(incluir_momento_actual=True)
    fecha_pasada = Asamblea.fecha_hora < ahora
    orden_predeterminado = [
        db.case((fecha_futura, 0), else_=1).asc(),
        db.case(
            (fecha_futura, Asamblea.fecha_hora),
            else_=None,
        ).asc(),
        db.case(
            (fecha_pasada, Asamblea.fecha_hora),
            else_=None,
        ).desc(),
    ]
    consulta, valores = preparar_listado(
        db.select(Asamblea),
        request.args,
        [Asamblea.titulo, Asamblea.orden_del_dia],
        {
            "fecha": Asamblea.fecha_hora,
            "titulo": Asamblea.titulo,
        },
        orden_predeterminado,
        filtros={
            "tipo": {
                tipo: Asamblea.tipo == tipo
                for tipo in Asamblea.TIPOS
            },
            "periodo": {
                "proximas": fecha_futura,
                "pasadas": fecha_pasada,
            },
        },
    )
    paginacion = paginar_consulta(
        consulta,
        request.args.get("pagina"),
        current_app.config["POR_PAGINA"],
    )
    return render_template(
        "asambleas/listado.html",
        asambleas=paginacion.items,
        paginacion=paginacion,
        valores=valores,
        parametros_paginacion=valores,
        hay_filtros=bool(
            valores["q"] or valores["tipo"] or valores["periodo"]
        ),
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
