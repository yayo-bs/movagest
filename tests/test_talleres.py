"""Pruebas de talleres e inscripciones.

Cubren permisos, plazas, transiciones de inscripción y operaciones de gestión.
"""

from datetime import datetime, timedelta, timezone

from app.extensiones import db
from app.models import Inscripcion, Taller
from tests.conftest import iniciar_sesion


def crear_taller(usuario, **cambios):
    datos = {
        "titulo": "Taller de danza",
        "descripcion": "Actividad de prueba",
        "fecha_hora": datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc),
        "lugar": "Sala principal",
        "plazas": 3,
        "creado_por": usuario,
    }
    datos.update(cambios)
    taller = Taller(**datos)
    db.session.add(taller)
    db.session.commit()
    return taller


def datos_taller(**cambios):
    datos = {
        "titulo": "Taller de danza",
        "descripcion": "Actividad de prueba",
        "fecha_hora": "2030-01-01T12:00",
        "lugar": "Sala principal",
        "plazas": "3",
    }
    datos.update(cambios)
    return datos


def test_socio_autenticado_ve_listado_y_detalle(
    cliente, crear_usuario
):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    taller = crear_taller(socio)
    iniciar_sesion(cliente, socio)

    listado = cliente.get("/talleres/")
    detalle = cliente.get(f"/talleres/{taller.id}")

    assert listado.status_code == 200
    assert b"Taller de danza" in listado.data
    assert b"3 de 3 plazas libres" in listado.data
    assert detalle.status_code == 200
    assert b"Inscribirme" in detalle.data


def test_usuario_no_autenticado_se_redirige_al_login(
    cliente, crear_usuario
):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    taller = crear_taller(socio)

    for ruta in ("/talleres/", f"/talleres/{taller.id}"):
        respuesta = cliente.get(ruta)
        assert respuesta.status_code == 302
        assert respuesta.headers["Location"].startswith("/auth/login?next=")


def test_socio_recibe_403_en_rutas_de_gestion(
    cliente, crear_usuario
):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    taller = crear_taller(socio)
    iniciar_sesion(cliente, socio)

    respuestas = [
        cliente.get("/talleres/nuevo"),
        cliente.get(f"/talleres/{taller.id}/editar"),
        cliente.post(f"/talleres/{taller.id}/borrar"),
    ]
    assert [respuesta.status_code for respuesta in respuestas] == [403, 403, 403]


def test_administrador_crea_edita_y_borra_taller(
    cliente, crear_usuario
):
    administrador = crear_usuario(
        email="admin@example.com", rol="administrador", estado="activo"
    )
    iniciar_sesion(cliente, administrador)

    respuesta_crear = cliente.post(
        "/talleres/nuevo",
        data=datos_taller(),
        follow_redirects=True,
    )
    taller = db.session.scalar(
        db.select(Taller).where(Taller.titulo == "Taller de danza")
    )
    assert respuesta_crear.status_code == 200
    assert taller is not None
    assert taller.creado_por_id == administrador.id

    respuesta_editar = cliente.post(
        f"/talleres/{taller.id}/editar",
        data=datos_taller(titulo="Taller actualizado", plazas="5"),
        follow_redirects=True,
    )
    assert respuesta_editar.status_code == 200
    assert taller.titulo == "Taller actualizado"
    assert taller.plazas == 5

    respuesta_borrar = cliente.post(
        f"/talleres/{taller.id}/borrar",
        data={"confirmar_borrado": "si"},
    )
    assert respuesta_borrar.status_code == 302
    assert db.session.get(Taller, taller.id) is None


def test_socio_se_inscribe_y_baja_las_plazas_libres(
    cliente, crear_usuario
):
    administrador = crear_usuario(
        email="admin@example.com", rol="administrador", estado="activo"
    )
    socio = crear_usuario(email="socio@example.com", estado="activo")
    taller = crear_taller(administrador, plazas=2)
    iniciar_sesion(cliente, socio)

    respuesta = cliente.post(f"/talleres/{taller.id}/inscribirse")

    assert respuesta.status_code == 302
    assert db.session.get(Taller, taller.id).plazas_libres == 1
    assert db.session.scalar(db.select(Inscripcion)) is not None


def test_inscripcion_duplicada_no_crea_fila_adicional(
    cliente, crear_usuario
):
    administrador = crear_usuario(
        email="admin@example.com", rol="administrador", estado="activo"
    )
    socio = crear_usuario(email="socio@example.com", estado="activo")
    taller = crear_taller(administrador)
    iniciar_sesion(cliente, socio)

    cliente.post(f"/talleres/{taller.id}/inscribirse")
    respuesta = cliente.post(
        f"/talleres/{taller.id}/inscribirse",
        follow_redirects=True,
    )

    inscripciones = db.session.scalars(
        db.select(Inscripcion).where(Inscripcion.taller_id == taller.id)
    ).all()
    assert len(inscripciones) == 1
    assert "Ya estás inscrito en este taller.".encode() in respuesta.data


def test_inscripcion_a_taller_completo_es_rechazada(
    cliente, crear_usuario
):
    administrador = crear_usuario(
        email="admin@example.com", rol="administrador", estado="activo"
    )
    socio_uno = crear_usuario(email="uno@example.com", estado="activo")
    socio_dos = crear_usuario(email="dos@example.com", estado="activo")
    taller = crear_taller(administrador, plazas=1)
    db.session.add(Inscripcion(taller=taller, usuario=socio_uno))
    db.session.commit()
    iniciar_sesion(cliente, socio_dos)

    respuesta = cliente.post(
        f"/talleres/{taller.id}/inscribirse",
        follow_redirects=True,
    )

    assert db.session.scalar(
        db.select(Inscripcion).where(Inscripcion.usuario_id == socio_dos.id)
    ) is None
    assert "El taller está completo".encode() in respuesta.data


def test_inscripcion_a_taller_pasado_es_rechazada(cliente, crear_usuario):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    taller = crear_taller(
        socio,
        fecha_hora=datetime.now(timezone.utc) - timedelta(days=1),
    )
    iniciar_sesion(cliente, socio)

    respuesta = cliente.post(
        f"/talleres/{taller.id}/inscribirse",
        follow_redirects=True,
    )

    assert db.session.scalar(
        db.select(Inscripcion).where(Inscripcion.taller_id == taller.id)
    ) is None
    assert "ya ha finalizado".encode() in respuesta.data


def test_cancelar_inscripcion_libera_plaza_y_no_cancela_otra(
    app, cliente, crear_usuario
):
    administrador = crear_usuario(
        email="admin@example.com", rol="administrador", estado="activo"
    )
    socio_uno = crear_usuario(email="uno@example.com", estado="activo")
    socio_dos = crear_usuario(email="dos@example.com", estado="activo")
    taller = crear_taller(administrador, plazas=2)
    inscripcion = Inscripcion(taller=taller, usuario=socio_uno)
    db.session.add(inscripcion)
    db.session.commit()
    cliente_dos = app.test_client()
    iniciar_sesion(cliente_dos, socio_dos)

    cliente_dos.post(f"/talleres/{taller.id}/cancelar")
    assert db.session.scalar(
        db.select(Inscripcion).where(Inscripcion.id == inscripcion.id)
    ) is not None

    cliente_uno = app.test_client()
    iniciar_sesion(cliente_uno, socio_uno)
    respuesta = cliente_uno.post(f"/talleres/{taller.id}/cancelar")

    assert respuesta.status_code == 302
    assert db.session.scalar(
        db.select(Inscripcion).where(Inscripcion.id == inscripcion.id)
    ) is None
    assert db.session.get(Taller, taller.id).plazas_libres == 2


def test_edicion_no_reduce_plazas_bajo_inscritos(
    cliente, crear_usuario
):
    administrador = crear_usuario(
        email="admin@example.com", rol="administrador", estado="activo"
    )
    socio = crear_usuario(email="socio@example.com", estado="activo")
    taller = crear_taller(administrador, plazas=2)
    db.session.add(Inscripcion(taller=taller, usuario=socio))
    db.session.commit()
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.post(
        f"/talleres/{taller.id}/editar",
        data=datos_taller(plazas="0"),
    )

    assert respuesta.status_code == 200
    assert db.session.get(Taller, taller.id).plazas == 2
    assert "No puedes establecer menos plazas".encode() in respuesta.data


def test_borrar_taller_elimina_inscripciones(cliente, crear_usuario):
    administrador = crear_usuario(
        email="admin@example.com", rol="administrador", estado="activo"
    )
    socio = crear_usuario(email="socio@example.com", estado="activo")
    taller = crear_taller(administrador)
    db.session.add(Inscripcion(taller=taller, usuario=socio))
    db.session.commit()
    id_taller = taller.id
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.post(
        f"/talleres/{id_taller}/borrar",
        data={"confirmar_borrado": "si"},
    )

    assert respuesta.status_code == 302
    assert db.session.get(Taller, id_taller) is None
    assert db.session.scalar(
        db.select(Inscripcion).where(Inscripcion.taller_id == id_taller)
    ) is None


def test_detalle_muestra_inscritos_solo_a_administrador(
    app, cliente, crear_usuario
):
    administrador = crear_usuario(
        email="admin@example.com", rol="administrador", estado="activo"
    )
    socio = crear_usuario(email="socio@example.com", estado="activo")
    taller = crear_taller(administrador)
    db.session.add(Inscripcion(taller=taller, usuario=socio))
    db.session.commit()

    iniciar_sesion(cliente, socio)
    respuesta_socio = cliente.get(f"/talleres/{taller.id}")
    assert b"Socios inscritos" not in respuesta_socio.data

    cliente_admin = app.test_client()
    iniciar_sesion(cliente_admin, administrador)
    respuesta_admin = cliente_admin.get(f"/talleres/{taller.id}")
    assert b"Socios inscritos" in respuesta_admin.data
    assert b"socio@example.com" in respuesta_admin.data


def test_listado_ordena_talleres_por_fecha_ascendente(
    cliente, crear_usuario
):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    crear_taller(
        socio,
        titulo="Taller posterior",
        fecha_hora=datetime(2030, 2, 1, tzinfo=timezone.utc),
    )
    crear_taller(
        socio,
        titulo="Taller anterior",
        fecha_hora=datetime(2030, 1, 1, tzinfo=timezone.utc),
    )
    iniciar_sesion(cliente, socio)

    respuesta = cliente.get("/talleres/")

    assert respuesta.data.index(b"Taller anterior") < respuesta.data.index(
        b"Taller posterior"
    )


def test_listado_busca_en_titulo_y_descripcion(cliente, crear_usuario):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    crear_taller(socio, titulo="Danza", descripcion="Coreografía flamenca")
    crear_taller(socio, titulo="Música", descripcion="Ensayo de percusión")
    iniciar_sesion(cliente, socio)

    respuesta = cliente.get("/talleres/?q=FLAMENCA")

    assert b"Danza" in respuesta.data
    assert b"M\xc3\xbasica" not in respuesta.data


def test_listado_sin_coincidencias_muestra_mensaje_claro(
    cliente, crear_usuario
):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    crear_taller(socio)
    iniciar_sesion(cliente, socio)

    respuesta = cliente.get("/talleres/?q=inexistente")

    assert b"No se encontraron resultados" in respuesta.data
    assert b"No hay talleres publicados" not in respuesta.data


def test_listado_ordena_por_titulo_en_ambas_direcciones(
    cliente, crear_usuario
):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    crear_taller(socio, titulo="Zeta")
    crear_taller(socio, titulo="Alfa")
    iniciar_sesion(cliente, socio)

    ascendente = cliente.get("/talleres/?orden=titulo&dir=asc")
    descendente = cliente.get("/talleres/?orden=titulo&dir=desc")

    assert ascendente.data.index(b"Alfa") < ascendente.data.index(b"Zeta")
    assert descendente.data.index(b"Zeta") < descendente.data.index(b"Alfa")


def test_filtro_muestra_solo_talleres_con_plazas_libres(
    cliente, crear_usuario
):
    administrador = crear_usuario(
        email="admin@example.com", rol="administrador", estado="activo"
    )
    socio = crear_usuario(email="socio@example.com", estado="activo")
    crear_taller(administrador, titulo="Con plazas", plazas=2)
    completo = crear_taller(administrador, titulo="Completo", plazas=1)
    db.session.add(Inscripcion(taller=completo, usuario=socio))
    db.session.commit()
    iniciar_sesion(cliente, socio)

    respuesta = cliente.get("/talleres/?plazas_libres=si")

    assert b"Con plazas" in respuesta.data
    assert b"Completo" not in respuesta.data
