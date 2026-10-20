"""Consultas resumidas para la página de inicio autenticada.

Usa los mismos modelos y permisos de lectura de los listados existentes.
"""

from datetime import datetime, timezone

from app.asambleas.consultas import filtro_asambleas_futuras
from app.extensiones import db
from app.models import (
    Asamblea,
    Documento,
    Inscripcion,
    Noticia,
    Taller,
    Usuario,
)
from app.talleres.consultas import filtro_talleres_con_plazas_libres


def obtener_ultimas_noticias():
    return db.session.scalars(
        db.select(Noticia)
        .order_by(Noticia.fecha_publicacion.desc())
        .limit(3)
    ).all()


def obtener_proxima_asamblea():
    return db.session.scalar(
        db.select(Asamblea)
        .where(filtro_asambleas_futuras())
        .order_by(Asamblea.fecha_hora.asc())
        .limit(1)
    )


def obtener_talleres_disponibles():
    ahora = datetime.now(timezone.utc).replace(tzinfo=None)
    return db.session.scalars(
        db.select(Taller)
        .where(Taller.fecha_hora > ahora, filtro_talleres_con_plazas_libres())
        .order_by(Taller.fecha_hora.asc())
        .limit(3)
    ).all()


def obtener_inscripciones_futuras(id_usuario):
    ahora = datetime.now(timezone.utc).replace(tzinfo=None)
    return db.session.scalars(
        db.select(Inscripcion)
        .join(Inscripcion.taller)
        .where(
            Inscripcion.usuario_id == id_usuario,
            Taller.fecha_hora > ahora,
        )
        .order_by(Taller.fecha_hora.asc())
    ).all()


def obtener_ultimos_documentos():
    return db.session.scalars(
        db.select(Documento)
        .order_by(Documento.fecha_subida.desc())
        .limit(3)
    ).all()


def contar_altas_pendientes():
    return db.session.scalar(
        db.select(db.func.count(Usuario.id)).where(
            Usuario.estado == "pendiente"
        )
    )
