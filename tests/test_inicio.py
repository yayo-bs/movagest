"""Pruebas del inicio autenticado.

Verifican contenido, permisos y resúmenes de los módulos existentes.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.extensiones import db
from app.models import Asamblea, Documento, Inscripcion, Noticia, Taller


def iniciar_sesion(cliente, usuario):
    with cliente.session_transaction() as sesion:
        sesion["_user_id"] = str(usuario.id)
        sesion["_fresh"] = True


def fecha_futura(dias=2):
    return datetime.now(timezone.utc) + timedelta(days=dias)


def crear_taller(usuario, titulo, fecha, plazas=3):
    taller = Taller(
        titulo=titulo,
        descripcion="Descripción de prueba",
        fecha_hora=fecha,
        lugar="Sala principal",
        plazas=plazas,
        creado_por=usuario,
    )
    db.session.add(taller)
    db.session.commit()
    return taller


def test_inicio_sin_sesion_redirige_al_login(cliente):
    respuesta = cliente.get("/inicio")

    assert respuesta.status_code == 302
    assert respuesta.headers["Location"].startswith("/auth/login?next=")


@pytest.mark.parametrize("estado", ["pendiente", "rechazado", "baja"])
def test_usuario_no_activo_no_accede_al_inicio(
    cliente, crear_usuario, estado
):
    usuario = crear_usuario(estado=estado)
    iniciar_sesion(cliente, usuario)

    respuesta = cliente.get("/inicio")

    assert respuesta.status_code == 302
    assert respuesta.headers["Location"].startswith("/auth/login?next=")


def test_socio_activo_ve_saludo_y_bloques_principales(
    cliente, crear_usuario
):
    socio = crear_usuario(estado="activo")
    iniciar_sesion(cliente, socio)

    respuesta = cliente.get("/inicio")

    assert respuesta.status_code == 200
    assert b"Hola, Ana" in respuesta.data
    assert b"ltimas noticias" in respuesta.data
    assert b"Pr\xc3\xb3xima asamblea" in respuesta.data
    assert b"Talleres con plazas libres" in respuesta.data
    assert b"Mis inscripciones" in respuesta.data
    assert b"ltimos documentos" in respuesta.data


def test_inicio_muestra_tres_noticias_mas_recientes(
    cliente, crear_usuario
):
    socio = crear_usuario(estado="activo")
    ahora = datetime.now(timezone.utc)
    for numero in range(5):
        db.session.add(
            Noticia(
                titulo=f"Noticia {numero}",
                contenido="Contenido",
                fecha_publicacion=ahora + timedelta(minutes=numero),
                autor=socio,
            )
        )
    db.session.commit()
    iniciar_sesion(cliente, socio)

    respuesta = cliente.get("/inicio")

    assert respuesta.data.index(b"Noticia 4") < respuesta.data.index(b"Noticia 3")
    assert b"Noticia 2" in respuesta.data
    assert b"Noticia 1" not in respuesta.data
    assert b"Noticia 0" not in respuesta.data
    assert b"/noticias/5" in respuesta.data
    assert ahora.strftime("%d/%m/%Y").encode() in respuesta.data
    assert b"Ver todas" in respuesta.data


def test_inicio_muestra_tres_documentos_mas_recientes(
    cliente, crear_usuario
):
    socio = crear_usuario(estado="activo")
    ahora = datetime.now(timezone.utc)
    for numero in range(5):
        db.session.add(
            Documento(
                titulo=f"Documento {numero}",
                categoria="documento",
                nombre_original=f"archivo{numero}.pdf",
                nombre_archivo=f"archivo{numero}.pdf",
                fecha_subida=ahora + timedelta(minutes=numero),
                subido_por=socio,
            )
        )
    db.session.commit()
    iniciar_sesion(cliente, socio)

    respuesta = cliente.get("/inicio")

    assert respuesta.data.index(b"Documento 4") < respuesta.data.index(
        b"Documento 3"
    )
    assert b"Documento 2" in respuesta.data
    assert b"Documento 1" not in respuesta.data
    assert b"Documento 0" not in respuesta.data
    assert b'href="/documentos/"' in respuesta.data


def test_inicio_muestra_solo_la_proxima_asamblea_futura(
    cliente, crear_usuario
):
    socio = crear_usuario(estado="activo")
    fecha_cercana = fecha_futura(3)
    db.session.add_all(
        [
            Asamblea(
                titulo="Asamblea pasada",
                tipo="ordinaria",
                fecha_hora=fecha_futura(-2),
                lugar="Sala antigua",
                orden_del_dia="Punto pasado",
                autor=socio,
            ),
            Asamblea(
                titulo="Asamblea cercana",
                tipo="extraordinaria",
                fecha_hora=fecha_cercana,
                lugar="Sala principal",
                orden_del_dia="Punto futuro",
                autor=socio,
            ),
            Asamblea(
                titulo="Asamblea lejana",
                tipo="ordinaria",
                fecha_hora=fecha_futura(8),
                lugar="Sala secundaria",
                orden_del_dia="Punto lejano",
                autor=socio,
            ),
        ]
    )
    db.session.commit()
    iniciar_sesion(cliente, socio)

    respuesta = cliente.get("/inicio")

    assert b"Asamblea cercana" in respuesta.data
    assert b"Asamblea pasada" not in respuesta.data
    assert b"Asamblea lejana" not in respuesta.data
    assert b"Extraordinaria" in respuesta.data
    assert b"Sala principal" in respuesta.data
    assert b"/asambleas/2" in respuesta.data
    assert fecha_cercana.strftime("%d/%m/%Y").encode() in respuesta.data
    assert fecha_cercana.strftime("%H:%M").encode() in respuesta.data


def test_inicio_muestra_hasta_tres_talleres_futuros_con_plazas(
    cliente, crear_usuario
):
    socio = crear_usuario(estado="activo")
    admin = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    for numero in range(4):
        crear_taller(admin, f"Taller libre {numero}", fecha_futura(numero + 1))
    taller_completo = crear_taller(
        admin, "Taller completo", fecha_futura(1), plazas=1
    )
    db.session.add(Inscripcion(taller=taller_completo, usuario=admin))
    crear_taller(admin, "Taller pasado", fecha_futura(-1))
    db.session.commit()
    iniciar_sesion(cliente, socio)

    respuesta = cliente.get("/inicio")

    assert b"Taller libre 0" in respuesta.data
    assert b"Taller libre 1" in respuesta.data
    assert b"Taller libre 2" in respuesta.data
    assert b"Taller libre 3" not in respuesta.data
    assert b"Taller completo" not in respuesta.data
    assert b"Taller pasado" not in respuesta.data


def test_mis_inscripciones_solo_incluye_usuario_y_talleres_futuros(
    cliente, crear_usuario
):
    socio = crear_usuario(email="ana@example.com", estado="activo")
    otra_socia = crear_usuario(email="otra@example.com", estado="activo")
    admin = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    taller_propio = crear_taller(admin, "Inscripción de Ana", fecha_futura(2))
    taller_ajeno = crear_taller(admin, "Inscripción de otra", fecha_futura(3))
    taller_pasado = crear_taller(admin, "Inscripción pasada", fecha_futura(-2))
    db.session.add_all(
        [
            Inscripcion(taller=taller_propio, usuario=socio),
            Inscripcion(taller=taller_ajeno, usuario=otra_socia),
            Inscripcion(taller=taller_pasado, usuario=socio),
        ]
    )
    db.session.commit()
    iniciar_sesion(cliente, socio)

    respuesta = cliente.get("/inicio")
    bloque = respuesta.data.split(b'id="mis-inscripciones"', 1)[1].split(
        b"</section>", 1
    )[0]

    assert "Inscripción de Ana".encode() in bloque
    assert "Inscripción de otra".encode() not in bloque
    assert "Inscripción pasada".encode() not in bloque


def test_inicio_muestra_mensajes_si_los_bloques_estan_vacios(
    cliente, crear_usuario
):
    socio = crear_usuario(estado="activo")
    iniciar_sesion(cliente, socio)

    respuesta = cliente.get("/inicio")

    assert b"No hay noticias publicadas." in respuesta.data
    assert b"No hay asambleas convocadas" in respuesta.data
    assert b"No hay pr\xc3\xb3ximos talleres con plazas libres." in respuesta.data
    assert b"No tienes inscripciones a talleres futuros." in respuesta.data
    assert b"No hay documentos disponibles." in respuesta.data


def test_administrador_ve_bloque_y_numero_de_altas_pendientes(
    cliente, crear_usuario
):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    crear_usuario(email="pendiente1@example.com", estado="pendiente")
    crear_usuario(email="pendiente2@example.com", estado="pendiente")
    crear_usuario(email="activo@example.com", estado="activo")
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.get("/inicio")

    assert b"Administraci\xc3\xb3n" in respuesta.data
    assert b"Solicitudes pendientes: 2" in respuesta.data
    assert b"estado=pendiente" in respuesta.data
    assert b"Crear noticia" in respuesta.data
    assert b"Crear convocatoria de Asamblea" in respuesta.data
    assert "Gestión de socios".encode() in respuesta.data


def test_socio_no_ve_bloque_ni_datos_de_administracion(
    cliente, crear_usuario
):
    socio = crear_usuario(estado="activo")
    crear_usuario(email="secreto@example.com", estado="pendiente")
    iniciar_sesion(cliente, socio)

    respuesta = cliente.get("/inicio")

    assert "Administración".encode() not in respuesta.data
    assert b"Solicitudes pendientes" not in respuesta.data
    assert b"secreto@example.com" not in respuesta.data


def test_usuario_autenticado_que_visita_login_va_a_inicio(
    cliente, crear_usuario
):
    socio = crear_usuario(estado="activo")
    iniciar_sesion(cliente, socio)

    respuesta = cliente.get("/auth/login")

    assert respuesta.status_code == 302
    assert respuesta.headers["Location"].endswith("/inicio")


def test_ruta_antigua_auth_inicio_ya_no_existe(cliente):
    assert cliente.get("/auth/inicio").status_code == 404


@pytest.mark.parametrize(
    ("estado", "destino"),
    [(True, "/inicio"), (False, "/")],
)
def test_navegacion_principal_enlaza_inicio_segun_sesion(
    cliente, crear_usuario, estado, destino
):
    if estado:
        socio = crear_usuario(estado="activo")
        iniciar_sesion(cliente, socio)

    respuesta = cliente.get("/")

    assert respuesta.status_code == 200
    assert f'href="{destino}"'.encode() in respuesta.data
