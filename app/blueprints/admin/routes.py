"""Rutas administrativas para gestionar solicitudes de alta.

Incluye el ciclo de vida de los usuarios y la revisión de sus altas.
"""

from datetime import datetime, timezone

from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user

from app.blueprints.admin import bp
from app.decoradores import solo_administradores
from app.extensiones import db
from app.models import Inscripcion, Taller, Usuario
from app.utilidades.listados import paginar_consulta, preparar_listado


@bp.get("/altas")
@solo_administradores
def listar_altas():
    estado_recibido = request.args.get("estado")
    if estado_recibido and estado_recibido not in Usuario.ESTADOS:
        flash("El filtro de estado no es válido.", "warning")

    consulta, valores = preparar_listado(
        db.select(Usuario),
        request.args,
        [Usuario.nombre, Usuario.apellidos, Usuario.email],
        {
            "nombre": Usuario.nombre,
            "fecha": Usuario.fecha_alta,
        },
        Usuario.fecha_alta.asc(),
        filtros={
            "estado": {
                estado: Usuario.estado == estado
                for estado in Usuario.ESTADOS
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
        "admin/altas.html",
        usuarios=paginacion.items,
        paginacion=paginacion,
        valores=valores,
        parametros_paginacion=valores,
        hay_filtros=bool(valores["q"] or valores["estado"]),
    )


def _fecha_en_utc(fecha):
    if fecha.tzinfo is None:
        return fecha.replace(tzinfo=timezone.utc)
    return fecha


def _cancelar_inscripciones_futuras(usuario):
    ahora = datetime.now(timezone.utc)
    inscripciones = db.session.scalars(
        db.select(Inscripcion)
        .join(Taller)
        .where(Inscripcion.usuario_id == usuario.id)
    ).all()
    for inscripcion in inscripciones:
        if _fecha_en_utc(inscripcion.taller.fecha_hora) > ahora:
            db.session.delete(inscripcion)


def _tiene_contenido_asociado(usuario):
    return bool(
        usuario.noticias
        or usuario.documentos
        or usuario.inscripciones_talleres
        or usuario.talleres_creados
    )


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


@bp.post("/altas/<int:id_usuario>/reconsiderar")
@solo_administradores
def reconsiderar_alta(id_usuario):
    usuario = db.session.get(Usuario, id_usuario)
    if usuario is None:
        abort(404)
    if usuario.estado != "rechazado":
        flash("Solo se pueden reconsiderar usuarios rechazados.", "warning")
        return redirect(url_for("admin.listar_altas"))

    usuario.estado = "pendiente"
    db.session.commit()
    flash(f"El alta de {usuario.nombre} vuelve a estar pendiente.", "success")
    return redirect(url_for("admin.listar_altas"))


@bp.post("/altas/<int:id_usuario>/eliminar")
@solo_administradores
def eliminar_usuario_rechazado(id_usuario):
    usuario = db.session.get(Usuario, id_usuario)
    if usuario is None:
        abort(404)
    if usuario.id == current_user.id:
        flash("No puedes eliminar tu propia cuenta.", "warning")
    elif usuario.es_administrador():
        flash("No se pueden eliminar cuentas de administrador.", "warning")
    elif usuario.estado != "rechazado":
        flash("Solo se pueden eliminar usuarios rechazados.", "warning")
    elif _tiene_contenido_asociado(usuario):
        flash(
            "No se puede eliminar el usuario porque tiene contenido asociado.",
            "warning",
        )
    elif request.form.get("confirmar_borrado") != "si":
        flash("Confirma que deseas eliminar definitivamente este usuario.", "warning")
    else:
        db.session.delete(usuario)
        db.session.commit()
        flash("El usuario rechazado se ha eliminado definitivamente.", "success")
        return redirect(url_for("admin.listar_altas"))

    return redirect(url_for("admin.listar_altas"))


@bp.post("/usuarios/<int:id_usuario>/dar-baja")
@solo_administradores
def dar_de_baja_usuario(id_usuario):
    usuario = db.session.get(Usuario, id_usuario)
    if usuario is None:
        abort(404)
    if usuario.id == current_user.id:
        flash("No puedes darte de baja a ti mismo.", "warning")
    elif not usuario.esta_activo():
        flash("Solo se puede dar de baja a usuarios activos.", "warning")
    elif usuario.es_administrador() and _administradores_activos() <= 1:
        flash("No se puede dar de baja al último administrador activo.", "warning")
    elif request.form.get("confirmar_baja") != "si":
        flash("Confirma que deseas dar de baja a este usuario.", "warning")
    elif not usuario.dar_de_baja():
        flash("Solo se puede dar de baja a usuarios activos.", "warning")
    else:
        _cancelar_inscripciones_futuras(usuario)
        db.session.commit()
        flash(f"Se ha dado de baja a {usuario.nombre}.", "success")
        return redirect(url_for("admin.listar_altas"))

    return redirect(url_for("admin.listar_altas"))


def _administradores_activos():
    return db.session.scalar(
        db.select(db.func.count(Usuario.id)).where(
            Usuario.rol == "administrador",
            Usuario.estado == "activo",
        )
    )


@bp.post("/usuarios/<int:id_usuario>/reactivar")
@solo_administradores
def reactivar_usuario(id_usuario):
    usuario = db.session.get(Usuario, id_usuario)
    if usuario is None:
        abort(404)
    if not usuario.reactivar():
        flash("Solo se pueden reactivar usuarios que estén de baja.", "warning")
        return redirect(url_for("admin.listar_altas"))

    db.session.commit()
    flash(f"Se ha reactivado a {usuario.nombre}.", "success")
    return redirect(url_for("admin.listar_altas"))
