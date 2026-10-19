"""Modelo de archivos compartidos por la asociación.

Guarda metadatos y referencia al archivo almacenado fuera de static.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import validates

from app.extensiones import db


class Documento(db.Model):
    """Representa un documento o acta subida por una persona usuaria."""

    CATEGORIAS = ("documento", "acta")

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    categoria = db.Column(db.String(20), nullable=False)
    nombre_original = db.Column(db.String(255), nullable=False)
    nombre_archivo = db.Column(db.String(255), unique=True, nullable=False)
    fecha_subida = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    subido_por_id = db.Column(
        db.Integer,
        db.ForeignKey("usuario.id"),
        nullable=False,
    )
    subido_por = db.relationship("Usuario", backref="documentos")

    @validates("categoria")
    def validar_categoria(self, clave, valor):
        if valor not in self.CATEGORIAS:
            raise ValueError(f"Categoría no permitida: {valor}")
        return valor

    def __repr__(self):
        return f"<Documento {self.titulo!r}>"
