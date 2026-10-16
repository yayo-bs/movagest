"""Modelo de noticias publicadas por los usuarios de la asociación.

Cada noticia conserva su autor y la fecha UTC de publicación.
"""

from datetime import datetime, timezone

from app.extensiones import db


class Noticia(db.Model):
    """Representa una noticia visible para las personas usuarias."""

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    contenido = db.Column(db.Text, nullable=False)
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
    autor = db.relationship("Usuario", backref="noticias")

    def __repr__(self):
        return f"<Noticia {self.titulo!r}>"
