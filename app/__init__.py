"""Factory y configuración de la aplicación MovaGest.

Registra extensiones, blueprints y comandos de la aplicación.
"""

import os

from dotenv import load_dotenv
from flask import Flask

load_dotenv()

from app.config import CONFIGURACIONES
from app.extensiones import csrf, db, login_manager
from app.utilidades.formatos import anio_actual, formato_euros, formato_fecha


def create_app(configuracion=None):
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

    if not app.config.get("CARPETA_SUBIDAS"):
        app.config["CARPETA_SUBIDAS"] = os.path.join(
            app.instance_path, "subidas"
        )
    if not app.testing:
        os.makedirs(app.config["CARPETA_SUBIDAS"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Inicia sesión para acceder a esta página."
    login_manager.login_message_category = "info"
    csrf.init_app(app)
    app.add_template_filter(formato_euros, "euros")
    app.add_template_filter(formato_fecha, "fecha_es")
    app.add_template_global(anio_actual, "anio_actual")

    from app.blueprints.admin import bp as admin_bp
    from app.blueprints.auth import bp as auth_bp
    from app.blueprints.main import bp as main_bp
    from app.asambleas import bp as asambleas_bp
    from app.comandos import registrar_comandos
    from app.documentos import bp as documentos_bp
    from app.finanzas import bp as finanzas_bp
    from app.noticias import bp as noticias_bp
    from app.talleres import bp as talleres_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(noticias_bp)
    app.register_blueprint(asambleas_bp)
    app.register_blueprint(documentos_bp)
    app.register_blueprint(finanzas_bp)
    app.register_blueprint(talleres_bp)
    registrar_comandos(app)

    return app
