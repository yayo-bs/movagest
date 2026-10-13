import os

from dotenv import load_dotenv
from flask import Flask

load_dotenv()

from app.config import CONFIGURACIONES
from app.extensions import csrf, db


def create_app(configuracion=None):
    """Crea y configura una instancia de la aplicación Flask."""
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    if configuracion is None:
        configuracion = os.getenv("FLASK_CONFIG", "desarrollo")

    if isinstance(configuracion, str):
        try:
            clase_configuracion = CONFIGURACIONES[configuracion]
        except KeyError as error:
            raise ValueError(
                f"Configuración desconocida: {configuracion}"
            ) from error
        app.config.from_object(clase_configuracion)
    else:
        app.config.from_object(configuracion)

    db.init_app(app)
    csrf.init_app(app)

    from app.blueprints.auth import bp as auth_bp
    from app.blueprints.main import bp as main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    return app
