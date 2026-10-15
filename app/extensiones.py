"""Extensiones compartidas por los módulos de la aplicación.

Se inicializan sobre la instancia Flask desde la factory.
"""

from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect


db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
