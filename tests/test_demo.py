"""Pruebas del comando para cargar y reiniciar datos de demostración.

Verifican marcas, límites de acceso, archivos y conservación de datos ajenos.
"""

from collections import Counter
from datetime import date
from pathlib import Path

from app.extensiones import db
from app.models import (
    Actividad,
    Asamblea,
    Cuota,
    Documento,
    Inscripcion,
    Movimiento,
    Noticia,
    Taller,
    Usuario,
)
from tests.conftest import iniciar_sesion


def ejecutar_demo(app, *argumentos):
    """Invoca el comando Flask con los argumentos indicados."""
    return app.test_cli_runner().invoke(args=["cargar-demo", *argumentos])


def contar(modelo):
    """Cuenta las filas del modelo dentro de la base de pruebas."""
    return db.session.scalar(db.select(db.func.count()).select_from(modelo))


def test_primera_carga_crea_el_conjunto_esperado(app):
    resultado = ejecutar_demo(app)

    usuarios = db.session.scalars(db.select(Usuario)).all()
    estados = Counter(usuario.estado for usuario in usuarios)
    cuotas = db.session.scalars(db.select(Cuota)).all()

    assert resultado.exit_code == 0, resultado.output
    assert estados == {
        "activo": 8,
        "pendiente": 2,
        "rechazado": 1,
        "baja": 1,
    }
    assert contar(Noticia) == 5
    assert contar(Documento) == 4
    assert contar(Taller) == 4
    assert contar(Inscripcion) == 11
    assert contar(Asamblea) == 2
    assert len(cuotas) == 12
    assert contar(Movimiento) == 10
    assert contar(Actividad) > 30
    assert Counter(cuota.estado for cuota in cuotas) == {
        "pagada": 5,
        "pendiente": 6,
        "anulada": 1,
    }
    assert "Usuarios: 12" in resultado.output
    assert "junta@demo.example.com" in resultado.output


def test_segunda_carga_no_duplica_registros_ni_archivos(app):
    primera = ejecutar_demo(app)
    conteos_primera = {
        modelo: contar(modelo)
        for modelo in (
            Usuario,
            Noticia,
            Documento,
            Taller,
            Inscripcion,
            Asamblea,
            Cuota,
            Movimiento,
            Actividad,
        )
    }
    documentos_primera = sorted(
        Path(app.config["CARPETA_SUBIDAS"]).iterdir()
    )

    segunda = ejecutar_demo(app)

    assert primera.exit_code == segunda.exit_code == 0
    assert {
        modelo: contar(modelo)
        for modelo in conteos_primera
    } == conteos_primera
    assert sorted(
        Path(app.config["CARPETA_SUBIDAS"]).iterdir()
    ) == documentos_primera
    assert "Usuarios: 0" in segunda.output


def test_reiniciar_conserva_usuarios_y_datos_que_no_son_demo(
    app, crear_usuario
):
    usuario_real = crear_usuario(
        email="persona-real@example.org",
        nombre="Cuenta Real",
        estado="activo",
    )
    noticia_real = Noticia(
        titulo="Aviso privado de prueba",
        contenido="Este contenido no pertenece a la demo.",
        autor=usuario_real,
    )
    db.session.add(noticia_real)
    db.session.commit()
    ejecutar_demo(app)
    ids_documentos_anteriores = {
        documento.nombre_archivo
        for documento in db.session.scalars(db.select(Documento)).all()
    }

    resultado = ejecutar_demo(app, "--reiniciar")

    assert resultado.exit_code == 0, resultado.output
    assert db.session.get(Usuario, usuario_real.id) is not None
    assert db.session.get(Noticia, noticia_real.id) is not None
    assert contar(Noticia) == 6
    assert contar(Documento) == 4
    assert "Usuarios: 12" in resultado.output
    ids_documentos_nuevos = {
        documento.nombre_archivo
        for documento in db.session.scalars(db.select(Documento)).all()
        if documento.titulo.startswith("DEMO |")
    }
    assert ids_documentos_nuevos.isdisjoint(ids_documentos_anteriores)
    assert all(
        (Path(app.config["CARPETA_SUBIDAS"]) / nombre).is_file()
        for nombre in ids_documentos_nuevos
    )


def test_produccion_bloquea_la_carga_salvo_con_forzar(app):
    app.config["MODO_PRODUCCION"] = True

    bloqueado = ejecutar_demo(app)
    autorizado = ejecutar_demo(app, "--forzar")

    assert bloqueado.exit_code != 0
    assert "está bloqueada en producción" in bloqueado.output
    assert autorizado.exit_code == 0, autorizado.output
    assert contar(Noticia) == 5


def test_faltan_tablas_indica_ejecutar_init_db(app):
    db.drop_all()

    resultado = ejecutar_demo(app)

    assert resultado.exit_code != 0
    assert "flask --app run.py init-db" in resultado.output


def test_taller_completo_rechaza_inscripcion_por_la_ruta_real(app):
    resultado = ejecutar_demo(app)
    assert resultado.exit_code == 0
    taller = db.session.scalar(
        db.select(Taller).where(
            Taller.titulo == "DEMO | Suelo y suspensión completo"
        )
    )
    socio = db.session.scalar(
        db.select(Usuario).where(
            Usuario.email == "socia05@demo.example.com"
        )
    )
    cliente = app.test_client()
    iniciar_sesion(cliente, socio)

    respuesta = cliente.post(
        f"/talleres/{taller.id}/inscribirse",
        follow_redirects=True,
    )

    assert taller.esta_completo
    assert taller.plazas_ocupadas == taller.plazas
    assert "El taller está completo".encode() in respuesta.data
    assert db.session.scalar(
        db.select(Inscripcion).where(
            Inscripcion.taller_id == taller.id,
            Inscripcion.usuario_id == socio.id,
        )
    ) is None


def test_recibos_pagados_y_anulados_son_correlativos_por_anio(app):
    resultado = ejecutar_demo(app)
    assert resultado.exit_code == 0

    cuotas = db.session.scalars(
        db.select(Cuota).where(Cuota.numero_recibo.is_not(None))
    ).all()
    por_anio = {}
    for cuota in cuotas:
        anio = cuota.fecha_pago.year
        por_anio.setdefault(anio, []).append(
            int(cuota.numero_recibo[-4:])
        )
    for numeros in por_anio.values():
        assert sorted(numeros) == list(range(1, len(numeros) + 1))

    pagadas = [cuota for cuota in cuotas if cuota.estado == "pagada"]
    assert len(pagadas) == 5
    assert all(cuota.numero_recibo is not None for cuota in pagadas)
    assert any(cuota.estado == "anulada" for cuota in cuotas)
    assert date.today().year in por_anio


def test_credenciales_demo_acceden_a_actividad_inicio_y_pdf(
    app, cliente
):
    resultado = ejecutar_demo(app)
    assert resultado.exit_code == 0

    inicio_sesion = cliente.post(
        "/auth/login",
        data={
            "email": "junta@demo.example.com",
            "password": "Danza-MovaDemo-2026!",
        },
        follow_redirects=True,
    )
    actividad = cliente.get("/admin/actividad")
    assert inicio_sesion.status_code == 200
    assert actividad.status_code == 200
    assert b"DEMO" in actividad.data

    cliente.post("/auth/logout")
    socio = cliente.post(
        "/auth/login",
        data={
            "email": "socia01@demo.example.com",
            "password": "Danza-MovaDemo-2026!",
        },
        follow_redirects=True,
    )
    assert socio.status_code == 200

    documentos = db.session.scalars(db.select(Documento)).all()
    assert len(documentos) == 4
    for documento in documentos:
        ruta = Path(app.config["CARPETA_SUBIDAS"]) / documento.nombre_archivo
        assert ruta.is_file()
        descarga = cliente.get(
            f"/documentos/{documento.id}/descargar"
        )
        assert descarga.status_code == 200
        assert descarga.mimetype == "application/pdf"
