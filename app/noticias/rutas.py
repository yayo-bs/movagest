"""Rutas para consultar y administrar noticias.

La lista y el detalle requieren sesión; las modificaciones requieren rol admin.
"""

from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from app.decoradores import solo_administradores
from app.extensiones import db
from app.models import Noticia
from app.noticias import bp
from app.noticias.formularios import FormularioNoticia
from app.utilidades.listados import paginar_consulta, preparar_listado


@bp.get("/")
@login_required
def listar_noticias():
    consulta, valores = preparar_listado(
        db.select(Noticia),
        request.args,
        [Noticia.titulo, Noticia.contenido],
        {
            "fecha": Noticia.fecha_publicacion,
            "titulo": Noticia.titulo,
        },
        Noticia.fecha_publicacion.desc(),
    )
    paginacion = paginar_consulta(
        consulta,
        request.args.get("pagina"),
        current_app.config["POR_PAGINA"],
    )
    return render_template(
        "noticias/lista.html",
        noticias=paginacion.items,
        paginacion=paginacion,
        valores=valores,
        parametros_paginacion=valores,
        hay_filtros=bool(valores["q"]),
    )


@bp.get("/<int:id_noticia>")
@login_required
def ver_noticia(id_noticia):
    noticia = db.get_or_404(Noticia, id_noticia)
    return render_template("noticias/detalle.html", noticia=noticia)


@bp.route("/nueva", methods=["GET", "POST"])
@solo_administradores
def nueva_noticia():
    formulario = FormularioNoticia()
    if formulario.validate_on_submit():
        noticia = Noticia(
            titulo=formulario.titulo.data.strip(),
            contenido=formulario.contenido.data.strip(),
            autor=current_user,
        )
        db.session.add(noticia)
        db.session.commit()
        flash("La noticia se ha creado correctamente.", "success")
        return redirect(url_for("noticias.ver_noticia", id_noticia=noticia.id))

    return render_template("noticias/formulario.html", formulario=formulario)


@bp.route("/<int:id_noticia>/editar", methods=["GET", "POST"])
@solo_administradores
def editar_noticia(id_noticia):
    noticia = db.get_or_404(Noticia, id_noticia)
    formulario = FormularioNoticia(obj=noticia)
    if formulario.validate_on_submit():
        noticia.titulo = formulario.titulo.data.strip()
        noticia.contenido = formulario.contenido.data.strip()
        db.session.commit()
        flash("La noticia se ha actualizado correctamente.", "success")
        return redirect(url_for("noticias.ver_noticia", id_noticia=noticia.id))

    return render_template(
        "noticias/formulario.html",
        formulario=formulario,
        noticia=noticia,
    )


@bp.post("/<int:id_noticia>/borrar")
@solo_administradores
def borrar_noticia(id_noticia):
    noticia = db.get_or_404(Noticia, id_noticia)
    if request.form.get("confirmar_borrado") != "si":
        flash("Confirma que deseas borrar esta noticia.", "warning")
        return redirect(url_for("noticias.ver_noticia", id_noticia=noticia.id))

    db.session.delete(noticia)
    db.session.commit()
    flash("La noticia se ha borrado correctamente.", "success")
    return redirect(url_for("noticias.listar_noticias"))
