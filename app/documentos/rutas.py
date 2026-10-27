"""Rutas para listar, descargar y gestionar documentos y actas.

Solo el equipo administrador puede subir o borrar archivos.
"""

import os
import zipfile
from uuid import uuid4

from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.decoradores import solo_administradores
from app.documentos import bp
from app.documentos.formularios import FormularioDocumento
from app.extensiones import db
from app.models import Documento
from app.utilidades.actividad import registrar
from app.utilidades.listados import paginar_consulta, preparar_listado


def _guardar_documento(formulario, usuario):
    archivo = formulario.archivo.data
    nombre_original = archivo.filename
    nombre_seguro = secure_filename(nombre_original or "")
    extension = nombre_seguro.rsplit(".", 1)[1].lower()
    nombre_archivo = f"{uuid4().hex}.{extension}"
    carpeta = current_app.config["CARPETA_SUBIDAS"]
    os.makedirs(carpeta, exist_ok=True)
    archivo.save(os.path.join(carpeta, nombre_archivo))

    documento = Documento(
        titulo=formulario.titulo.data.strip(),
        descripcion=formulario.descripcion.data.strip() or None,
        categoria=formulario.categoria.data,
        nombre_original=nombre_original,
        nombre_archivo=nombre_archivo,
        subido_por=usuario,
    )
    db.session.add(documento)
    registrar(
        "documento.subir",
        f"Subido el archivo «{documento.titulo}» ({documento.categoria})",
        usuario=usuario,
    )
    db.session.commit()


def _firma_archivo_valida(archivo, extension):
    stream = archivo.stream
    posicion_inicial = stream.tell()
    try:
        firma = stream.read(8)
        if extension == "pdf":
            return firma.startswith(b"%PDF-")
        if extension in ("jpg", "jpeg"):
            return firma.startswith(b"\xff\xd8\xff")
        if extension == "png":
            return firma.startswith(b"\x89PNG\r\n\x1a\n")
        if extension == "doc":
            return firma.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")
        if extension in ("docx", "odt"):
            stream.seek(posicion_inicial)
            with zipfile.ZipFile(stream) as contenedor:
                archivos = set(contenedor.namelist())
                if extension == "docx":
                    return (
                        "[Content_Types].xml" in archivos
                        and "word/document.xml" in archivos
                    )
                return (
                    "mimetype" in archivos
                    and contenedor.read("mimetype")
                    == b"application/vnd.oasis.opendocument.text"
                )
        return False
    except (zipfile.BadZipFile, KeyError, OSError):
        return False
    finally:
        stream.seek(posicion_inicial)


def _eliminar_documento(documento):
    ruta_archivo = os.path.join(
        current_app.config["CARPETA_SUBIDAS"],
        documento.nombre_archivo,
    )
    if os.path.isfile(ruta_archivo):
        try:
            os.remove(ruta_archivo)
        except OSError:
            current_app.logger.exception(
                "No se pudo borrar el archivo físico del documento %s.",
                documento.id,
            )
    db.session.delete(documento)
    registrar(
        "documento.eliminar",
        f"Eliminado el archivo «{documento.titulo}» ({documento.categoria})",
    )
    db.session.commit()


@bp.get("/")
@login_required
def listar_documentos():
    consulta, valores = preparar_listado(
        db.select(Documento),
        request.args,
        [Documento.titulo, Documento.descripcion],
        {
            "fecha": Documento.fecha_subida,
            "titulo": Documento.titulo,
        },
        Documento.fecha_subida.desc(),
        filtros={
            "categoria": {
                categoria: Documento.categoria == categoria
                for categoria in Documento.CATEGORIAS
            }
        },
    )
    paginacion = paginar_consulta(
        consulta,
        request.args.get("pagina"),
        current_app.config["POR_PAGINA"],
    )
    return render_template(
        "documentos/lista.html",
        documentos=paginacion.items,
        paginacion=paginacion,
        valores=valores,
        parametros_paginacion=valores,
        hay_filtros=bool(valores["q"] or valores["categoria"]),
    )


@bp.get("/<int:id_documento>/descargar")
@login_required
def descargar_documento(id_documento):
    documento = db.get_or_404(Documento, id_documento)
    carpeta = current_app.config["CARPETA_SUBIDAS"]
    if not os.path.isfile(os.path.join(carpeta, documento.nombre_archivo)):
        abort(404)
    return send_from_directory(
        carpeta,
        documento.nombre_archivo,
        as_attachment=True,
        download_name=documento.nombre_original,
    )


@bp.route("/nuevo", methods=["GET", "POST"])
@solo_administradores
def nuevo_documento():
    formulario = FormularioDocumento()
    if formulario.validate_on_submit():
        nombre_seguro = secure_filename(
            formulario.archivo.data.filename or ""
        )
        extension = nombre_seguro.rsplit(".", 1)[1].lower()
        if not _firma_archivo_valida(formulario.archivo.data, extension):
            formulario.archivo.errors.append(
                "El contenido no coincide con el tipo de archivo indicado."
            )
            return render_template(
                "documentos/formulario.html",
                formulario=formulario,
            )
        _guardar_documento(formulario, current_user)
        flash("El archivo se ha subido correctamente.", "success")
        return redirect(url_for("documentos.listar_documentos"))

    return render_template("documentos/formulario.html", formulario=formulario)


@bp.post("/<int:id_documento>/borrar")
@solo_administradores
def borrar_documento(id_documento):
    documento = db.get_or_404(Documento, id_documento)
    if request.form.get("confirmar_borrado") != "si":
        flash("Confirma que deseas eliminar este archivo.", "warning")
        return redirect(url_for("documentos.listar_documentos"))

    _eliminar_documento(documento)
    flash("El archivo se ha eliminado correctamente.", "success")
    return redirect(url_for("documentos.listar_documentos"))
