"""Pruebas del módulo de noticias.

Comprueban autenticación, permisos, operaciones administrativas y orden.
"""

from datetime import datetime, timedelta, timezone

from app.extensiones import db
from app.models import Noticia


def iniciar_sesion(cliente, usuario):
    with cliente.session_transaction() as sesion:
        sesion["_user_id"] = str(usuario.id)
        sesion["_fresh"] = True


def crear_noticia(autor, titulo="Noticia", contenido="Contenido"):
    noticia = Noticia(titulo=titulo, contenido=contenido, autor=autor)
    db.session.add(noticia)
    db.session.commit()
    return noticia


def datos_noticia(**cambios):
    datos = {"titulo": "Título de prueba", "contenido": "Texto de la noticia"}
    datos.update(cambios)
    return datos


def test_socio_autenticado_ve_listado_y_detalle(cliente, crear_usuario):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    noticia = crear_noticia(socio)
    iniciar_sesion(cliente, socio)

    listado = cliente.get("/noticias/")
    detalle = cliente.get(f"/noticias/{noticia.id}")

    assert listado.status_code == 200
    assert b"Noticia" in listado.data
    assert detalle.status_code == 200
    assert b"Contenido" in detalle.data


def test_usuario_no_autenticado_se_redirige_al_login(
    cliente, crear_usuario
):
    usuario = crear_usuario(email="socio@example.com", estado="activo")
    noticia = crear_noticia(usuario)

    for ruta in ("/noticias/", f"/noticias/{noticia.id}"):
        respuesta = cliente.get(ruta)
        assert respuesta.status_code == 302
        assert respuesta.headers["Location"].startswith("/auth/login?next=")


def test_socio_no_puede_crear_editar_ni_borrar_noticias(
    cliente, crear_usuario
):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    noticia = crear_noticia(socio)
    iniciar_sesion(cliente, socio)

    respuestas = [
        cliente.get("/noticias/nueva"),
        cliente.get(f"/noticias/{noticia.id}/editar"),
        cliente.post(f"/noticias/{noticia.id}/borrar"),
    ]

    assert [respuesta.status_code for respuesta in respuestas] == [403, 403, 403]
    assert db.session.get(Noticia, noticia.id) is not None


def test_administrador_crea_edita_y_borra_noticia(cliente, crear_usuario):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    iniciar_sesion(cliente, administrador)

    respuesta_creacion = cliente.post(
        "/noticias/nueva",
        data=datos_noticia(),
        follow_redirects=True,
    )
    noticia = db.session.scalar(
        db.select(Noticia).where(Noticia.titulo == "Título de prueba")
    )
    assert respuesta_creacion.status_code == 200
    assert noticia is not None
    assert noticia.autor_id == administrador.id

    respuesta_edicion = cliente.post(
        f"/noticias/{noticia.id}/editar",
        data=datos_noticia(
            titulo="Título actualizado",
            contenido="Contenido actualizado",
        ),
        follow_redirects=True,
    )
    assert respuesta_edicion.status_code == 200
    assert noticia.titulo == "Título actualizado"
    assert noticia.contenido == "Contenido actualizado"

    respuesta_borrado = cliente.post(
        f"/noticias/{noticia.id}/borrar",
        data={"confirmar_borrado": "si"},
        follow_redirects=True,
    )
    assert respuesta_borrado.status_code == 200
    assert db.session.get(Noticia, noticia.id) is None


def test_borrar_requiere_confirmacion(cliente, crear_usuario):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    noticia = crear_noticia(administrador)
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.post(
        f"/noticias/{noticia.id}/borrar",
        follow_redirects=True,
    )

    assert respuesta.status_code == 200
    assert db.session.get(Noticia, noticia.id) is not None
    assert "Confirma que deseas eliminar esta noticia.".encode() in respuesta.data


def test_detalle_de_noticia_inexistente_devuelve_404(cliente, crear_usuario):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    iniciar_sesion(cliente, socio)

    assert cliente.get("/noticias/999").status_code == 404


def test_listado_ordena_por_fecha_descendente(cliente, crear_usuario):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    noticia_antigua = crear_noticia(socio, titulo="Noticia antigua")
    noticia_reciente = crear_noticia(socio, titulo="Noticia reciente")
    noticia_antigua.fecha_publicacion = datetime.now(timezone.utc) - timedelta(days=1)
    noticia_reciente.fecha_publicacion = datetime.now(timezone.utc)
    db.session.commit()
    iniciar_sesion(cliente, socio)

    respuesta = cliente.get("/noticias/")

    assert respuesta.status_code == 200
    assert respuesta.data.index(b"Noticia reciente") < respuesta.data.index(
        b"Noticia antigua"
    )


def test_listado_busca_en_titulo_y_contenido(cliente, crear_usuario):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    crear_noticia(socio, "Ensayo", "Coreografía flamenca")
    crear_noticia(socio, "Concierto", "Música en directo")
    iniciar_sesion(cliente, socio)

    respuesta = cliente.get("/noticias/?q=FLAMENCA")

    assert b"Ensayo" in respuesta.data
    assert b"Concierto" not in respuesta.data


def test_listado_muestra_mensaje_si_busqueda_no_tiene_resultados(
    cliente, crear_usuario
):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    crear_noticia(socio)
    iniciar_sesion(cliente, socio)

    respuesta = cliente.get("/noticias/?q=inexistente")

    assert b"No se encontraron resultados" in respuesta.data
    assert b"Todav\xc3\xada no hay noticias publicadas" not in respuesta.data


def test_listado_ordena_por_titulo_en_ambas_direcciones(
    cliente, crear_usuario
):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    crear_noticia(socio, "Zeta")
    crear_noticia(socio, "Alfa")
    iniciar_sesion(cliente, socio)

    ascendente = cliente.get("/noticias/?orden=titulo&dir=asc")
    descendente = cliente.get("/noticias/?orden=titulo&dir=desc")

    assert ascendente.data.index(b"Alfa") < ascendente.data.index(b"Zeta")
    assert descendente.data.index(b"Zeta") < descendente.data.index(b"Alfa")
