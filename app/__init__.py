"""Factory y configuración de la aplicación MovaGest.

Registra extensiones, blueprints y comandos de la aplicación.
"""

import os

from dotenv import load_dotenv
from flask import Flask, render_template

load_dotenv()

from app.config import CONFIGURACIONES, aplicar_variables_entorno
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

    aplicar_variables_entorno(app.config)
    if not app.config.get("SECRET_KEY") and not app.config.get(
        "MODO_DESARROLLO"
    ) and not app.testing:
        raise RuntimeError(
            "Falta SECRET_KEY. Define una clave segura en el entorno o en .env "
            "antes de iniciar la aplicación en producción."
        )

    carpeta_subidas = app.config.get("CARPETA_SUBIDAS") or "subidas"
    if not os.path.isabs(carpeta_subidas):
        carpeta_subidas = os.path.join(app.instance_path, carpeta_subidas)
    app.config["CARPETA_SUBIDAS"] = carpeta_subidas

    ruta_subidas = os.path.realpath(carpeta_subidas)
    ruta_static = os.path.realpath(app.static_folder)
    try:
        dentro_de_static = (
            os.path.normcase(
                os.path.commonpath([ruta_subidas, ruta_static])
            )
            == os.path.normcase(ruta_static)
        )
    except ValueError:
        dentro_de_static = False
    if dentro_de_static:
        raise RuntimeError(
            "CARPETA_SUBIDAS no puede estar dentro de la carpeta static."
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

    @app.errorhandler(413)
    def archivo_demasiado_grande(_error):
        return (
            render_template(
                "errores/413.html",
                maximo_bytes=app.config["MAX_CONTENT_LENGTH"],
            ),
            413,
        )

    @app.errorhandler(403)
    def pagina_prohibida(_error):
        return render_template("errores/403.html"), 403

    @app.errorhandler(404)
    def pagina_no_encontrada(_error):
        return render_template("errores/404.html"), 404

    @app.errorhandler(500)
    def error_interno(_error):
        db.session.rollback()
        return render_template("errores/500.html"), 500

    return app
