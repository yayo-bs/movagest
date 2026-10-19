"""Pruebas del módulo de documentos y actas.

Usan la carpeta temporal de pruebas para no modificar instance/subidas.
"""

from datetime import datetime, timedelta, timezone
from io import BytesIO
import os

from app.extensiones import db
from app.models import Documento


def iniciar_sesion(cliente, usuario):
    with cliente.session_transaction() as sesion:
        sesion["_user_id"] = str(usuario.id)
        sesion["_fresh"] = True


def crear_documento(app, usuario, titulo, categoria, nombre="archivo.pdf"):
    documento = Documento(
        titulo=titulo,
        descripcion="Descripción de prueba",
        categoria=categoria,
        nombre_original=nombre,
        nombre_archivo=f"{titulo}.pdf",
        subido_por=usuario,
    )
    db.session.add(documento)
    db.session.commit()
    with open(
        os.path.join(app.config["CARPETA_SUBIDAS"], documento.nombre_archivo),
        "wb",
    ) as archivo:
        archivo.write(b"contenido de prueba")
    return documento


def datos_subida(nombre="informe.pdf", categoria="documento"):
    return {
        "titulo": "Informe",
        "descripcion": "Archivo de prueba",
        "categoria": categoria,
        "archivo": (BytesIO(b"contenido del PDF"), nombre),
    }


def test_socio_autenticado_lista_y_descarga_documento(
    app, cliente, crear_usuario
):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    documento = crear_documento(app, socio, "Informe", "documento")
    iniciar_sesion(cliente, socio)

    listado = cliente.get("/documentos/")
    descarga = cliente.get(f"/documentos/{documento.id}/descargar")

    assert listado.status_code == 200
    assert b"Informe" in listado.data
    assert descarga.status_code == 200
    assert descarga.headers["Content-Disposition"].startswith(
        "attachment; filename=archivo.pdf"
    )
    assert descarga.data == b"contenido de prueba"


def test_usuario_no_autenticado_es_redirigido_en_lista_y_descarga(
    app, cliente, crear_usuario
):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    documento = crear_documento(app, socio, "Informe", "documento")

    for ruta in ("/documentos/", f"/documentos/{documento.id}/descargar"):
        respuesta = cliente.get(ruta)
        assert respuesta.status_code == 302
        assert respuesta.headers["Location"].startswith("/auth/login?next=")


def test_socio_no_puede_subir_ni_borrar_documentos(
    app, cliente, crear_usuario
):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    documento = crear_documento(app, socio, "Informe", "documento")
    iniciar_sesion(cliente, socio)

    assert cliente.get("/documentos/nuevo").status_code == 403
    assert cliente.post(
        f"/documentos/{documento.id}/borrar"
    ).status_code == 403


def test_administrador_subida_valida_crea_registro_y_archivo(
    app, cliente, crear_usuario
):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.post(
        "/documentos/nuevo",
        data=datos_subida(),
        content_type="multipart/form-data",
    )
    documento = db.session.scalar(
        db.select(Documento).where(Documento.titulo == "Informe")
    )

    assert respuesta.status_code == 302
    assert respuesta.headers["Location"] == "/documentos/"
    assert "Content-Disposition" not in respuesta.headers
    assert documento is not None
    assert documento.subido_por_id == administrador.id
    assert documento.nombre_original == "informe.pdf"
    assert os.path.isfile(
        os.path.join(app.config["CARPETA_SUBIDAS"], documento.nombre_archivo)
    )


def test_extension_no_permitida_no_crea_registro_ni_archivo(
    app, cliente, crear_usuario
):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.post(
        "/documentos/nuevo",
        data=datos_subida(nombre="programa.exe"),
        content_type="multipart/form-data",
    )

    assert respuesta.status_code == 200
    assert b"El tipo de archivo no est\xc3\xa1 permitido." in respuesta.data
    assert db.session.scalar(
        db.select(Documento).where(Documento.titulo == "Informe")
    ) is None
    assert os.listdir(app.config["CARPETA_SUBIDAS"]) == []


def test_subida_sin_archivo_se_rechaza(cliente, crear_usuario):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.post(
        "/documentos/nuevo",
        data={
            "titulo": "Informe",
            "descripcion": "",
            "categoria": "documento",
        },
    )

    assert respuesta.status_code == 200
    assert "Selecciona un archivo.".encode() in respuesta.data


def test_archivo_supera_limite_muestra_mensaje_claro(
    app, cliente, crear_usuario
):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    iniciar_sesion(cliente, administrador)
    app.config["MAX_CONTENT_LENGTH"] = 64

    respuesta = cliente.post(
        "/documentos/nuevo",
        data=datos_subida(),
        content_type="multipart/form-data",
    )

    assert respuesta.status_code == 413
    assert "El archivo supera el tamaño máximo permitido de 10 MB.".encode() in respuesta.data


def test_filtro_por_categoria(cliente, crear_usuario, app):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    crear_documento(app, socio, "Acta de reunión", "acta")
    crear_documento(app, socio, "Guía", "documento")
    iniciar_sesion(cliente, socio)

    respuesta_actas = cliente.get("/documentos/?categoria=acta")
    respuesta_documentos = cliente.get("/documentos/?categoria=documento")

    assert b"Acta de reuni\xc3\xb3n" in respuesta_actas.data
    assert b"Gu\xc3\xada" not in respuesta_actas.data
    assert b"Gu\xc3\xada" in respuesta_documentos.data
    assert b"Acta de reuni\xc3\xb3n" not in respuesta_documentos.data


def test_borrar_elimina_registro_y_archivo(app, cliente, crear_usuario):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    documento = crear_documento(app, administrador, "Informe", "documento")
    ruta_archivo = os.path.join(
        app.config["CARPETA_SUBIDAS"], documento.nombre_archivo
    )
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.post(
        f"/documentos/{documento.id}/borrar",
        data={"confirmar_borrado": "si"},
    )

    assert respuesta.status_code == 302
    assert db.session.get(Documento, documento.id) is None
    assert not os.path.exists(ruta_archivo)


def test_descarga_de_id_inexistente_devuelve_404(cliente, crear_usuario):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    iniciar_sesion(cliente, socio)

    assert cliente.get("/documentos/999/descargar").status_code == 404


def test_subidas_mismo_nombre_original_no_se_sobrescriben(
    app, cliente, crear_usuario
):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    iniciar_sesion(cliente, administrador)

    for titulo in ("Informe primero", "Informe segundo"):
        respuesta = cliente.post(
            "/documentos/nuevo",
            data={
                "titulo": titulo,
                "descripcion": "",
                "categoria": "documento",
                "archivo": (BytesIO(titulo.encode()), "informe.pdf"),
            },
            content_type="multipart/form-data",
        )
        assert respuesta.status_code == 302

    documentos = db.session.scalars(db.select(Documento)).all()
    assert len(documentos) == 2
    assert documentos[0].nombre_original == documentos[1].nombre_original
    assert documentos[0].nombre_archivo != documentos[1].nombre_archivo
    for documento in documentos:
        with open(
            os.path.join(app.config["CARPETA_SUBIDAS"], documento.nombre_archivo),
            "rb",
        ) as archivo:
            assert archivo.read()
