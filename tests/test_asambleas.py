"""Pruebas del módulo de convocatorias de Asamblea.

Cubren acceso, permisos, validación y operaciones administrativas.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.extensiones import db
from app.models import Asamblea


def iniciar_sesion(cliente, usuario):
    with cliente.session_transaction() as sesion:
        sesion["_user_id"] = str(usuario.id)
        sesion["_fresh"] = True


def datos_asamblea(**cambios):
    fecha = (datetime.now(timezone.utc) + timedelta(days=5)).replace(
        second=0,
        microsecond=0,
        tzinfo=None,
    )
    datos = {
        "titulo": "Asamblea anual",
        "tipo": "ordinaria",
        "fecha_hora": fecha.strftime("%Y-%m-%dT%H:%M"),
        "lugar": "Centro cultural",
        "orden_del_dia": "Lectura del acta\nPresupuesto anual",
    }
    datos.update(cambios)
    return datos


def crear_asamblea(autor, titulo, fecha_hora):
    asamblea = Asamblea(
        titulo=titulo,
        tipo="ordinaria",
        fecha_hora=fecha_hora,
        lugar="Centro cultural",
        orden_del_dia="Lectura del acta",
        autor=autor,
    )
    db.session.add(asamblea)
    db.session.commit()
    return asamblea


def test_usuario_anonimo_se_redirige_al_login(cliente):
    respuesta = cliente.get("/asambleas/")

    assert respuesta.status_code == 302
    assert respuesta.headers["Location"].startswith("/auth/login?next=")


def test_socio_activo_ve_el_listado(cliente, crear_usuario):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    iniciar_sesion(cliente, socio)

    respuesta = cliente.get("/asambleas/")

    assert respuesta.status_code == 200
    assert b"Asambleas" in respuesta.data
    assert b"Nueva convocatoria" not in respuesta.data


@pytest.mark.parametrize("estado", ["pendiente", "baja"])
def test_usuario_no_activo_no_puede_entrar(cliente, crear_usuario, estado):
    usuario = crear_usuario(
        email=f"{estado}@example.com",
        estado=estado,
    )

    respuesta_login = cliente.post(
        "/auth/login",
        data={"email": usuario.email, "password": "clave-segura-123"},
    )
    respuesta_asambleas = cliente.get("/asambleas/")

    assert respuesta_login.status_code == 200
    assert respuesta_asambleas.status_code == 302
    assert respuesta_asambleas.headers["Location"].startswith(
        "/auth/login?next="
    )


def test_socio_no_puede_crear_editar_ni_eliminar(cliente, crear_usuario):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    asamblea = crear_asamblea(
        socio,
        "Convocatoria existente",
        datetime.now(timezone.utc) + timedelta(days=1),
    )
    iniciar_sesion(cliente, socio)

    respuestas = [
        cliente.get("/asambleas/nueva"),
        cliente.get(f"/asambleas/{asamblea.id}/editar"),
        cliente.post(f"/asambleas/{asamblea.id}/eliminar"),
    ]

    assert [respuesta.status_code for respuesta in respuestas] == [403, 403, 403]


def test_administrador_crea_convocatoria(cliente, crear_usuario):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.post(
        "/asambleas/nueva",
        data=datos_asamblea(),
        follow_redirects=True,
    )
    asamblea = db.session.scalar(
        db.select(Asamblea).where(Asamblea.titulo == "Asamblea anual")
    )

    assert respuesta.status_code == 200
    assert asamblea is not None
    assert asamblea.autor_id == administrador.id
    assert asamblea.tipo == "ordinaria"


def test_administrador_edita_convocatoria_y_permite_fecha_pasada(
    cliente, crear_usuario
):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    asamblea = crear_asamblea(
        administrador,
        "Convocatoria",
        datetime.now(timezone.utc) + timedelta(days=1),
    )
    iniciar_sesion(cliente, administrador)
    fecha_pasada = (datetime.now() - timedelta(days=2)).strftime(
        "%Y-%m-%dT%H:%M"
    )

    respuesta = cliente.post(
        f"/asambleas/{asamblea.id}/editar",
        data=datos_asamblea(
            titulo="Convocatoria editada",
            fecha_hora=fecha_pasada,
        ),
        follow_redirects=True,
    )

    assert respuesta.status_code == 200
    assert asamblea.titulo == "Convocatoria editada"
    assert not asamblea.es_futura


def test_administrador_elimina_con_confirmacion(cliente, crear_usuario):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    asamblea = crear_asamblea(
        administrador,
        "Convocatoria",
        datetime.now(timezone.utc) + timedelta(days=1),
    )
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.post(
        f"/asambleas/{asamblea.id}/eliminar",
        data={"confirmar_eliminacion": "si"},
        follow_redirects=True,
    )

    assert respuesta.status_code == 200
    assert db.session.get(Asamblea, asamblea.id) is None


def test_eliminacion_sin_confirmar_conserva_convocatoria(
    cliente, crear_usuario
):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    asamblea = crear_asamblea(
        administrador,
        "Convocatoria",
        datetime.now(timezone.utc) + timedelta(days=1),
    )
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.post(f"/asambleas/{asamblea.id}/eliminar")

    assert respuesta.status_code == 302
    assert db.session.get(Asamblea, asamblea.id) is not None


def test_formulario_rechaza_campos_vacios(cliente, crear_usuario):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    iniciar_sesion(cliente, administrador)

    respuesta = cliente.post(
        "/asambleas/nueva",
        data=datos_asamblea(titulo="", lugar="", orden_del_dia=""),
    )

    assert respuesta.status_code == 200
    assert b'class="error"' in respuesta.data
    assert db.session.scalar(db.select(Asamblea)) is None


def test_fecha_pasada_no_se_acepta_al_crear(cliente, crear_usuario):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    iniciar_sesion(cliente, administrador)
    fecha_pasada = (datetime.now() - timedelta(days=1)).strftime(
        "%Y-%m-%dT%H:%M"
    )

    respuesta = cliente.post(
        "/asambleas/nueva",
        data=datos_asamblea(fecha_hora=fecha_pasada),
    )

    assert respuesta.status_code == 200
    assert "La fecha no puede ser anterior a hoy.".encode() in respuesta.data
    assert db.session.scalar(db.select(Asamblea)) is None


def test_listado_separa_futuras_antes_de_pasadas(cliente, crear_usuario):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    pasada_antigua = crear_asamblea(
        socio,
        "Asamblea pasada antigua",
        datetime.now(timezone.utc) - timedelta(days=5),
    )
    pasada_reciente = crear_asamblea(
        socio,
        "Asamblea pasada reciente",
        datetime.now(timezone.utc) - timedelta(days=1),
    )
    futura_proxima = crear_asamblea(
        socio,
        "Asamblea futura próxima",
        datetime.now(timezone.utc) + timedelta(days=1),
    )
    futura_lejana = crear_asamblea(
        socio,
        "Asamblea futura lejana",
        datetime.now(timezone.utc) + timedelta(days=5),
    )
    iniciar_sesion(cliente, socio)

    respuesta = cliente.get("/asambleas/")

    assert respuesta.status_code == 200
    posiciones = [
        respuesta.data.index(titulo.encode())
        for titulo in (
            futura_proxima.titulo,
            futura_lejana.titulo,
            pasada_reciente.titulo,
            pasada_antigua.titulo,
        )
    ]
    assert posiciones == sorted(posiciones)


def test_detalle_inexistente_devuelve_404(cliente, crear_usuario):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    iniciar_sesion(cliente, socio)

    assert cliente.get("/asambleas/999").status_code == 404


def test_detalle_conserva_saltos_de_linea(cliente, crear_usuario):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    asamblea = crear_asamblea(
        socio,
        "Asamblea de prueba",
        datetime.now(timezone.utc) + timedelta(days=1),
    )
    asamblea.orden_del_dia = "Primer punto\nSegundo punto"
    db.session.commit()
    iniciar_sesion(cliente, socio)

    respuesta = cliente.get(f"/asambleas/{asamblea.id}")

    assert respuesta.status_code == 200
    assert b"Primer punto<br>Segundo punto" in respuesta.data


def test_modelo_rechaza_tipo_no_permitido():
    with pytest.raises(ValueError, match="Tipo de Asamblea no permitido"):
        Asamblea(
            titulo="Asamblea",
            tipo="urgente",
            fecha_hora=datetime.now(timezone.utc),
            lugar="Centro cultural",
            orden_del_dia="Puntos",
        )


def test_listado_busca_en_titulo_y_orden_del_dia(cliente, crear_usuario):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    convocatoria = crear_asamblea(
        socio,
        "Asamblea anual",
        datetime.now(timezone.utc) + timedelta(days=5),
    )
    convocatoria.orden_del_dia = "Presupuesto cultural"
    crear_asamblea(
        socio,
        "Asamblea vecinal",
        datetime.now(timezone.utc) + timedelta(days=6),
    )
    db.session.commit()
    iniciar_sesion(cliente, socio)

    respuesta = cliente.get("/asambleas/?q=CULTURAL")

    assert b"Asamblea anual" in respuesta.data
    assert b"Asamblea vecinal" not in respuesta.data


def test_listado_sin_coincidencias_muestra_mensaje_claro(
    cliente, crear_usuario
):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    iniciar_sesion(cliente, socio)

    respuesta = cliente.get("/asambleas/?q=inexistente")

    assert b"No se encontraron resultados" in respuesta.data
    assert b"No hay convocatorias publicadas" not in respuesta.data


def test_listado_ordena_por_titulo_ascendente_y_descendente(
    cliente, crear_usuario
):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    fecha = datetime.now(timezone.utc) + timedelta(days=2)
    crear_asamblea(socio, "Zeta", fecha)
    crear_asamblea(socio, "Alfa", fecha)
    iniciar_sesion(cliente, socio)

    ascendente = cliente.get("/asambleas/?orden=titulo&dir=asc")
    descendente = cliente.get("/asambleas/?orden=titulo&dir=desc")

    assert ascendente.data.index(b"Alfa") < ascendente.data.index(b"Zeta")
    assert descendente.data.index(b"Zeta") < descendente.data.index(b"Alfa")


def test_filtros_de_tipo_y_periodo_se_aplican_en_la_consulta(
    cliente, crear_usuario
):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    crear_asamblea(
        socio,
        "Ordinaria futura",
        datetime.now(timezone.utc) + timedelta(days=1),
    )
    extraordinaria = crear_asamblea(
        socio,
        "Extraordinaria pasada",
        datetime.now(timezone.utc) - timedelta(days=1),
    )
    extraordinaria.tipo = "extraordinaria"
    db.session.commit()
    iniciar_sesion(cliente, socio)

    respuesta = cliente.get(
        "/asambleas/?tipo=extraordinaria&periodo=pasadas"
    )

    assert extraordinaria.titulo.encode() in respuesta.data
    assert b"Ordinaria futura" not in respuesta.data


def test_orden_predeterminado_compuesto_se_conserva_entre_paginas(
    app, cliente, crear_usuario
):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    app.config["POR_PAGINA"] = 2
    crear_asamblea(
        socio,
        "Futura próxima",
        datetime.now(timezone.utc) + timedelta(days=1),
    )
    crear_asamblea(
        socio,
        "Futura lejana",
        datetime.now(timezone.utc) + timedelta(days=5),
    )
    crear_asamblea(
        socio,
        "Pasada reciente",
        datetime.now(timezone.utc) - timedelta(days=1),
    )
    crear_asamblea(
        socio,
        "Pasada intermedia",
        datetime.now(timezone.utc) - timedelta(days=3),
    )
    crear_asamblea(
        socio,
        "Pasada antigua",
        datetime.now(timezone.utc) - timedelta(days=5),
    )
    iniciar_sesion(cliente, socio)

    primera = cliente.get("/asambleas/")
    segunda = cliente.get("/asambleas/?pagina=2")
    tercera = cliente.get("/asambleas/?pagina=3")

    assert b"Futura pr\xc3\xb3xima" in primera.data
    assert b"Futura lejana" in primera.data
    assert b"Pasada reciente" in segunda.data
    assert b"Pasada intermedia" in segunda.data
    assert b"Pasada antigua" in tercera.data
