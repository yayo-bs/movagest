"""Rutas administrativas para gestionar cuotas y movimientos financieros.

Cada modificación comprueba el estado permitido y se realiza mediante POST.
"""

from datetime import date
from decimal import Decimal

from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required

from app.decoradores import solo_administradores
from app.extensiones import db
from app.finanzas import bp
from app.finanzas.consultas import (
    anios_resumen,
    obtener_cuotas_usuario,
    periodos_de_cuotas,
)
from app.finanzas.formularios import (
    FormularioEditarCuota,
    FormularioGenerarCuotas,
    FormularioMovimiento,
    FormularioPagoCuota,
)
from app.finanzas.recibos import generar_recibo_pdf
from app.finanzas.operaciones import (
    anular_cuota as anular_cuota_operacion,
    generar_cuotas as crear_cuotas_periodo,
    marcar_cuota_pagada,
)
from app.models import Cuota, Movimiento, Usuario
from app.utilidades.actividad import registrar
from app.utilidades.listados import paginar_consulta, preparar_listado


def _sumar_importes(consulta):
    """Suma importes con Decimal y evita convertir valores a float."""
    importes = db.session.scalars(consulta).all()
    return sum(importes, Decimal("0.00"))


def _resumen_financiero(anio):
    """Calcula ingresos, cuotas cobradas, gastos y saldo del año."""
    desde = date(anio, 1, 1)
    hasta = date(anio + 1, 1, 1)
    rango_movimientos = (
        Movimiento.fecha >= desde,
        Movimiento.fecha < hasta,
    )
    rango_cuotas = (
        Cuota.fecha_pago >= desde,
        Cuota.fecha_pago < hasta,
    )
    ingresos = _sumar_importes(
        db.select(Movimiento.importe).where(
            Movimiento.tipo == "ingreso",
            *rango_movimientos,
        )
    )
    gastos = _sumar_importes(
        db.select(Movimiento.importe).where(
            Movimiento.tipo == "gasto",
            *rango_movimientos,
        )
    )
    cuotas_cobradas = _sumar_importes(
        db.select(Cuota.importe).where(
            Cuota.estado == "pagada",
            *rango_cuotas,
        )
    )
    return {
        "ingresos": ingresos,
        "cuotas_cobradas": cuotas_cobradas,
        "gastos": gastos,
        "saldo": ingresos + cuotas_cobradas - gastos,
    }


def _guardar_movimiento(movimiento, formulario):
    """Copia al modelo los datos validados del formulario."""
    movimiento.tipo = formulario.tipo.data
    movimiento.concepto = formulario.concepto.data.strip()
    movimiento.importe = formulario.importe.data
    movimiento.fecha = formulario.fecha.data
    movimiento.categoria = formulario.categoria.data.strip() or None


@bp.get("/movimientos")
@solo_administradores
def listar_movimientos():
    anios = anios_resumen()
    valores_solicitados = request.args.to_dict()
    anio_seleccionado = valores_solicitados.get("anio", str(date.today().year))
    if anio_seleccionado not in {str(anio) for anio in anios}:
        anio_seleccionado = str(date.today().year)
    valores_solicitados["anio"] = anio_seleccionado

    filtros_anio = {
        str(anio): db.and_(
            Movimiento.fecha >= date(anio, 1, 1),
            Movimiento.fecha < date(anio + 1, 1, 1),
        )
        for anio in anios
    }
    consulta, valores = preparar_listado(
        db.select(Movimiento),
        valores_solicitados,
        [Movimiento.concepto],
        {
            "fecha": Movimiento.fecha,
            "concepto": Movimiento.concepto,
            "importe": Movimiento.importe,
        },
        Movimiento.fecha.desc(),
        filtros={
            "tipo": {
                tipo: Movimiento.tipo == tipo
                for tipo in Movimiento.TIPOS
            },
            "anio": filtros_anio,
        },
        direccion_por_defecto="desc",
    )
    paginacion = paginar_consulta(
        consulta,
        request.args.get("pagina"),
        current_app.config["POR_PAGINA"],
    )
    return render_template(
        "finanzas/movimientos.html",
        movimientos=paginacion.items,
        anios=anios,
        resumen=_resumen_financiero(int(anio_seleccionado)),
        paginacion=paginacion,
        valores=valores,
        parametros_paginacion=valores,
        hay_filtros=bool(
            valores["q"] or valores["tipo"] or request.args.get("anio")
        ),
    )


@bp.route("/movimientos/nuevo", methods=["GET", "POST"])
@solo_administradores
def nuevo_movimiento():
    formulario = FormularioMovimiento()
    if formulario.validate_on_submit():
        movimiento = Movimiento()
        _guardar_movimiento(movimiento, formulario)
        db.session.add(movimiento)
        registrar(
            "movimiento.crear",
            f"Creado el movimiento «{movimiento.concepto}»",
        )
        db.session.commit()
        flash("El movimiento se ha creado correctamente.", "success")
        return redirect(url_for("finanzas.listar_movimientos"))
    return render_template(
        "finanzas/formulario_movimiento.html",
        formulario=formulario,
        movimiento=None,
    )


@bp.route("/movimientos/<int:id_movimiento>/editar", methods=["GET", "POST"])
@solo_administradores
def editar_movimiento(id_movimiento):
    movimiento = db.get_or_404(Movimiento, id_movimiento)
    formulario = FormularioMovimiento(obj=movimiento)
    if formulario.validate_on_submit():
        _guardar_movimiento(movimiento, formulario)
        registrar(
            "movimiento.editar",
            f"Editado el movimiento «{movimiento.concepto}»",
        )
        db.session.commit()
        flash("El movimiento se ha actualizado correctamente.", "success")
        return redirect(url_for("finanzas.listar_movimientos"))
    return render_template(
        "finanzas/formulario_movimiento.html",
        formulario=formulario,
        movimiento=movimiento,
    )


@bp.post("/movimientos/<int:id_movimiento>/eliminar")
@solo_administradores
def eliminar_movimiento(id_movimiento):
    movimiento = db.get_or_404(Movimiento, id_movimiento)
    db.session.delete(movimiento)
    registrar(
        "movimiento.eliminar",
        f"Eliminado el movimiento «{movimiento.concepto}»",
    )
    db.session.commit()
    flash("El movimiento se ha eliminado correctamente.", "success")
    return redirect(url_for("finanzas.listar_movimientos"))


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
        cantidad = crear_cuotas_periodo(
            formulario.periodo.data,
            formulario.importe.data,
            usuario=current_user,
        )
        db.session.commit()
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
        try:
            marcar_cuota_pagada(cuota, fecha_pago, usuario=current_user)
        except ValueError as error:
            flash(str(error), "danger")
            return redirect(url_for("finanzas.listar_cuotas"))
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
    elif cuota.numero_recibo is not None:
        flash(
            "No se pueden eliminar cuotas con un recibo emitido.",
            "warning",
        )
    else:
        db.session.delete(cuota)
        registrar(
            "cuota.eliminar",
            f"Eliminada la cuota pendiente del periodo {cuota.periodo}",
        )
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
        anular_cuota_operacion(cuota, usuario=current_user)
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
        registrar(
            "cuota.reactivar",
            f"Reactivada la cuota del periodo {cuota.periodo} "
            f"de {cuota.usuario.nombre} {cuota.usuario.apellidos}".strip(),
        )
        db.session.commit()
        flash("La cuota se ha reactivado y conserva su recibo.", "success")
    return redirect(url_for("finanzas.listar_cuotas"))


@bp.get("/cuotas/<int:id_cuota>/recibo")
@login_required
def descargar_recibo(id_cuota):
    cuota = db.get_or_404(Cuota, id_cuota)
    if cuota.estado != "pagada":
        abort(404)
    if not current_user.es_administrador() and cuota.usuario_id != current_user.id:
        abort(404)

    archivo = generar_recibo_pdf(
        cuota,
        current_app.config.get("NOMBRE_ASOCIACION", "MovaGest"),
    )
    return send_file(
        archivo,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"{cuota.numero_recibo}.pdf",
    )


@bp.get("/mis-cuotas")
@login_required
def mis_cuotas():
    cuotas = obtener_cuotas_usuario(current_user.id)
    return render_template("finanzas/mis_cuotas.html", cuotas=cuotas)
