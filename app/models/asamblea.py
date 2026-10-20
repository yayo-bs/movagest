"""Modelo de convocatorias de Asamblea de la asociación.

Guarda los datos de cada convocatoria y calcula si todavía es futura.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import validates

from app.extensiones import db


class Asamblea(db.Model):
    """Representa una convocatoria de Asamblea publicada."""

    TIPOS = ("ordinaria", "extraordinaria")

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)
    fecha_hora = db.Column(db.DateTime(timezone=True), nullable=False)
    lugar = db.Column(db.String(200), nullable=False)
    orden_del_dia = db.Column(db.Text, nullable=False)
    fecha_publicacion = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    autor_id = db.Column(
        db.Integer,
        db.ForeignKey("usuario.id"),
        nullable=False,
    )
    autor = db.relationship("Usuario", backref="asambleas_publicadas")

    @validates("tipo")
    def validar_tipo(self, clave, valor):
        if valor not in self.TIPOS:
            raise ValueError(f"Tipo de Asamblea no permitido: {valor}")
        return valor

    @property
    def es_futura(self):
        """Indica si la fecha de la Asamblea es posterior al momento actual."""
        fecha = self.fecha_hora
        if fecha.tzinfo is None:
            fecha = fecha.replace(tzinfo=timezone.utc)
        return fecha > datetime.now(timezone.utc)

    def __repr__(self):
        return f"<Asamblea {self.titulo!r}>"
