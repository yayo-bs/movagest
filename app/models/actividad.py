"""Modelo del historial mínimo de acciones administrativas.

Conserva quién realizó una acción, cuándo ocurrió y una descripción legible.
"""

from datetime import datetime, timezone

from app.extensiones import db


class Actividad(db.Model):
    """Representa una acción registrada en el historial de la asociación."""

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuario.id", ondelete="SET NULL"),
        nullable=True,
    )
    usuario_nombre = db.Column(db.String(255), nullable=False)
    accion = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    usuario = db.relationship("Usuario", backref="actividades")
