"""Modelos para talleres e inscripciones de personas socias.

Las relaciones y restricciones mantienen el aforo y evitan duplicados.
"""

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, UniqueConstraint

from app.extensiones import db


class Taller(db.Model):
    """Representa una actividad con fecha, lugar y plazas limitadas."""

    __table_args__ = (
        CheckConstraint("plazas > 0", name="ck_taller_plazas_positivas"),
    )

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    fecha_hora = db.Column(db.DateTime(timezone=True), nullable=False)
    lugar = db.Column(db.String(200), nullable=False)
    plazas = db.Column(db.Integer, nullable=False)
    creado_por_id = db.Column(
        db.Integer,
        db.ForeignKey("usuario.id"),
        nullable=False,
    )
    creado_por = db.relationship("Usuario", backref="talleres_creados")
    inscripciones = db.relationship(
        "Inscripcion",
        back_populates="taller",
        cascade="all, delete-orphan",
    )

    @property
    def plazas_ocupadas(self):
        return len(self.inscripciones)

    @property
    def plazas_libres(self):
        return max(self.plazas - self.plazas_ocupadas, 0)

    @property
    def esta_completo(self):
        return self.plazas_libres == 0

    @property
    def esta_finalizado(self):
        fecha = self.fecha_hora
        if fecha.tzinfo is None:
            fecha = fecha.replace(tzinfo=timezone.utc)
        return fecha < datetime.now(timezone.utc)

    def esta_inscrito(self, usuario):
        return any(
            inscripcion.usuario_id == usuario.id
            for inscripcion in self.inscripciones
        )

    def __repr__(self):
        return f"<Taller {self.titulo!r}>"


class Inscripcion(db.Model):
    """Vincula de forma única a una persona con un taller."""

    __table_args__ = (
        UniqueConstraint(
            "taller_id",
            "usuario_id",
            name="uq_inscripcion_taller_usuario",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    taller_id = db.Column(
        db.Integer,
        db.ForeignKey("taller.id"),
        nullable=False,
    )
    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuario.id"),
        nullable=False,
    )
    fecha_inscripcion = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    taller = db.relationship("Taller", back_populates="inscripciones")
    usuario = db.relationship("Usuario", backref="inscripciones_talleres")
