"""Rutas administrativas para gestionar cuotas de socios.

Cada modificación comprueba el estado permitido y se realiza mediante POST.
"""

from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from app.decoradores import solo_administradores
from app.extensiones import db
from app.finanzas import bp
from app.finanzas.consultas import periodos_de_cuotas
from app.finanzas.formularios import (
    FormularioEditarCuota,
    FormularioGenerarCuotas,
    FormularioPagoCuota,
)
from app.models import Cuota, Usuario
from app.utilidades.listados import paginar_consulta, preparar_listado


def _generar_cuotas(periodo, importe):
    """Crea una cuota pendiente para cada socio activo que aún no la tenga."""
    socios = db.session.scalars(
        db.select(Usuario).where(
            Usuario.rol == "socio",
            Usuario.estado == "activo",
        )
    ).all()
    ids_con_cuota = set(
        db.session.scalars(
            db.select(Cuota.usuario_id).where(Cuota.periodo == periodo)
        ).all()
    )
    cuotas_nuevas = [
        Cuota(
            usuario=socio,
            periodo=periodo,
            importe=importe,
            estado="pendiente",
        )
        for socio in socios
        if socio.id not in ids_con_cuota
    ]
    db.session.add_all(cuotas_nuevas)
    db.session.commit()
    return len(cuotas_nuevas)


def _numero_recibo_siguiente(anio):
    """Calcula el siguiente número consecutivo para el año indicado."""
    ultimo_numero = db.session.scalar(
        db.select(db.func.max(Cuota.numero_recibo)).where(
            Cuota.numero_recibo.like(f"R-{anio}-%")
        )
    )
    if ultimo_numero is None:
        return 1
    return int(ultimo_numero[-4:]) + 1


@bp.get("/cuotas")
@solo_administradores
def listar_cuotas():
    periodos = periodos_de_cuotas()
    filtros_periodo = {
        str(periodo): Cuota.periodo == periodo
        for periodo in periodos
    }
    filtros_estado = {
        estado: Cuota.estado == estado
        for estado in Cuota.ESTADOS
    }
    consulta, valores = preparar_listado(
        db.select(Cuota)
        .join(Cuota.usuario)
        .options(db.joinedload(Cuota.usuario)),
        request.args,
        [
            Usuario.nombre,
            Usuario.apellidos,
            Usuario.email,
        ],
        {
            "periodo": Cuota.periodo,
            "socio": Usuario.apellidos,
            "estado": Cuota.estado,
        },
        [Cuota.periodo.desc(), Usuario.apellidos.asc(), Usuario.nombre.asc()],
        filtros={
            "estado": filtros_estado,
            "periodo": filtros_periodo,
        },
    )
    paginacion = paginar_consulta(
        consulta,
        request.args.get("pagina"),
        current_app.config["POR_PAGINA"],
    )
    return render_template(
        "finanzas/cuotas.html",
        cuotas=paginacion.items,
        periodos=periodos,
        paginacion=paginacion,
        valores=valores,
        parametros_paginacion=valores,
        hay_filtros=bool(
            valores["q"] or valores["estado"] or valores["periodo"]
        ),
    )


@bp.route("/cuotas/generar", methods=["GET", "POST"])
@solo_administradores
def generar_cuotas():
    formulario = FormularioGenerarCuotas()
    if formulario.validate_on_submit():
        cantidad = _generar_cuotas(
            formulario.periodo.data,
            formulario.importe.data,
        )
        flash(f"Se han creado {cantidad} cuotas pendientes.", "success")
        return redirect(url_for("finanzas.listar_cuotas"))
    return render_template(
        "finanzas/formulario_generar.html",
        formulario=formulario,
    )


@bp.route("/cuotas/<int:id_cuota>/editar", methods=["GET", "POST"])
@solo_administradores
def editar_cuota(id_cuota):
    cuota = db.get_or_404(Cuota, id_cuota)
    if cuota.estado != "pendiente":
        flash("Solo se puede editar el importe de una cuota pendiente.", "warning")
        return redirect(url_for("finanzas.listar_cuotas"))

    formulario = FormularioEditarCuota(obj=cuota)
    if formulario.validate_on_submit():
        cuota.importe = formulario.importe.data
        db.session.commit()
        flash("El importe de la cuota se ha actualizado.", "success")
        return redirect(url_for("finanzas.listar_cuotas"))
    return render_template(
        "finanzas/formulario_editar.html",
        formulario=formulario,
        cuota=cuota,
    )


@bp.route("/cuotas/<int:id_cuota>/pagar", methods=["GET", "POST"])
@solo_administradores
def pagar_cuota(id_cuota):
    cuota = db.get_or_404(Cuota, id_cuota)
    if cuota.estado != "pendiente":
        flash("Solo se puede pagar una cuota pendiente.", "warning")
        return redirect(url_for("finanzas.listar_cuotas"))

    formulario = FormularioPagoCuota()
    if formulario.validate_on_submit():
        fecha_pago = formulario.fecha_pago.data
        if cuota.numero_recibo is None:
            numero = _numero_recibo_siguiente(fecha_pago.year)
            if numero > 9999:
                flash(
                    "No se pueden asignar más recibos para este año.",
                    "danger",
                )
                return redirect(url_for("finanzas.listar_cuotas"))
            cuota.numero_recibo = f"R-{fecha_pago.year:04d}-{numero:04d}"

        cuota.fecha_pago = fecha_pago
        cuota.estado = "pagada"
        db.session.commit()
        flash(
            f"La cuota se ha pagado. Recibo {cuota.numero_recibo}.",
            "success",
        )
        return redirect(url_for("finanzas.listar_cuotas"))
    return render_template(
        "finanzas/formulario_pago.html",
        formulario=formulario,
        cuota=cuota,
    )


@bp.post("/cuotas/<int:id_cuota>/eliminar")
@solo_administradores
def eliminar_cuota(id_cuota):
    cuota = db.get_or_404(Cuota, id_cuota)
    if cuota.estado != "pendiente":
        flash("Solo se pueden eliminar cuotas pendientes.", "warning")
    else:
        db.session.delete(cuota)
        db.session.commit()
        flash("La cuota pendiente se ha eliminado.", "success")
    return redirect(url_for("finanzas.listar_cuotas"))


@bp.post("/cuotas/<int:id_cuota>/anular")
@solo_administradores
def anular_cuota(id_cuota):
    cuota = db.get_or_404(Cuota, id_cuota)
    if cuota.estado != "pagada":
        flash("Solo se pueden anular cuotas pagadas.", "warning")
    else:
        cuota.estado = "anulada"
        db.session.commit()
        flash("La cuota se ha anulado y el recibo se conserva.", "success")
    return redirect(url_for("finanzas.listar_cuotas"))


@bp.post("/cuotas/<int:id_cuota>/reactivar")
@solo_administradores
def reactivar_cuota(id_cuota):
    cuota = db.get_or_404(Cuota, id_cuota)
    if cuota.estado != "anulada":
        flash("Solo se pueden reactivar cuotas anuladas.", "warning")
    elif request.form.get("confirmar_reactivacion") != "si":
        flash("Confirma que deseas reactivar esta cuota.", "warning")
    else:
        cuota.estado = "pendiente"
        cuota.fecha_pago = None
        db.session.commit()
        flash("La cuota se ha reactivado y conserva su recibo.", "success")
    return redirect(url_for("finanzas.listar_cuotas"))
