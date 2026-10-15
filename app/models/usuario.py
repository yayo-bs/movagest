from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy.orm import validates
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensiones import db, login_manager


class Usuario(UserMixin, db.Model):
    """Representa a una persona socia o administradora de la asociación."""

    ROLES = ("socio", "administrador")
    ESTADOS = ("pendiente", "activo", "rechazado")

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    apellidos = db.Column(db.String(150))
    email = db.Column(db.String(255), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(20), nullable=False, default="socio")
    estado = db.Column(db.String(20), nullable=False, default="pendiente")
    fecha_alta = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    @validates("email")
    def normalizar_email(self, clave, valor):
        return valor.lower()

    @validates("rol")
    def validar_rol(self, clave, valor):
        if valor not in self.ROLES:
            raise ValueError(f"Rol no permitido: {valor}")
        return valor

    @validates("estado")
    def validar_estado(self, clave, valor):
        if valor not in self.ESTADOS:
            raise ValueError(f"Estado no permitido: {valor}")
        return valor

    def establecer_password(self, plano):
        """Guarda la contraseña únicamente en forma de hash."""
        self.password_hash = generate_password_hash(plano)

    def comprobar_password(self, plano):
        """Comprueba una contraseña frente al hash guardado."""
        return check_password_hash(self.password_hash, plano)

    def es_administrador(self):
        """Indica si la cuenta tiene el rol de administración."""
        return self.rol == "administrador"

    def esta_activo(self):
        """Indica si la cuenta está aprobada y activa."""
        return self.estado == "activo"

    def aprobar(self):
        """Activa la cuenta si todavía está pendiente de aprobación."""
        if self.estado != "pendiente":
            return False
        self.estado = "activo"
        return True

    def rechazar(self):
        """Rechaza la cuenta si todavía está pendiente de aprobación."""
        if self.estado != "pendiente":
            return False
        self.estado = "rechazado"
        return True


@login_manager.user_loader
def cargar_usuario(id_usuario):
    """Recupera una cuenta por su identificador de sesión."""
    try:
        id_numerico = int(id_usuario)
    except (TypeError, ValueError):
        return None

    return db.session.get(Usuario, id_numerico)
