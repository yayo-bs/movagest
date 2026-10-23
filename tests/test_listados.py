"""Pruebas unitarias de búsqueda, ordenación y paginación compartidas.

Verifican el helper común sin depender del contenido de una vista concreta.
"""

import html
import re
from datetime import date
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit

from sqlalchemy import case
from werkzeug.datastructures import MultiDict

from app.extensiones import db
from app.models import Documento, Movimiento, Noticia, Usuario
from app.utilidades.listados import paginar_consulta, preparar_listado


def crear_usuario_listado(email, nombre):
    usuario = Usuario(
        email=email,
        nombre=nombre,
        apellidos="Prueba",
        password_hash="hash",
        estado="activo",
    )
    db.session.add(usuario)
    db.session.commit()
    return usuario


def test_busqueda_no_distingue_mayusculas(app):
    crear_usuario_listado("ana@example.com", "Ana Danza")

    consulta, valores = preparar_listado(
        db.select(Usuario),
        MultiDict({"q": "aNa dAnZa"}),
        [Usuario.nombre],
        {"nombre": Usuario.nombre},
        Usuario.nombre.asc(),
    )

    assert db.session.scalars(consulta).one().nombre == "Ana Danza"
    assert valores["q"] == "aNa dAnZa"


def test_busqueda_escapa_porcentaje_y_guion_bajo(app):
    crear_usuario_listado("literal@example.com", "100%_real")
    crear_usuario_listado("comodin@example.com", "100Xareal")

    consulta, _ = preparar_listado(
        db.select(Usuario),
        MultiDict({"q": "%_"}),
        [Usuario.nombre],
        {},
        Usuario.nombre.asc(),
    )

    assert [usuario.nombre for usuario in db.session.scalars(consulta)] == [
        "100%_real"
    ]


def test_orden_acepta_solo_claves_de_la_lista_blanca(app):
    crear_usuario_listado("b@example.com", "Bea")
    crear_usuario_listado("a@example.com", "Ana")
    consulta, valores = preparar_listado(
        db.select(Usuario),
        MultiDict({"orden": "nombre", "dir": "asc"}),
        {"nombre": Usuario.nombre},
        {"nombre": Usuario.nombre},
        Usuario.nombre.desc(),
    )

    assert [usuario.nombre for usuario in db.session.scalars(consulta)] == [
        "Ana",
        "Bea",
    ]
    assert valores["orden"] == "nombre"


def test_orden_desconocido_usa_el_predeterminado(app):
    crear_usuario_listado("a@example.com", "Ana")
    crear_usuario_listado("b@example.com", "Bea")
    consulta, valores = preparar_listado(
        db.select(Usuario),
        MultiDict({"orden": "email"}),
        {"nombre": Usuario.nombre},
        {"nombre": Usuario.nombre},
        Usuario.nombre.desc(),
    )

    assert [usuario.nombre for usuario in db.session.scalars(consulta)] == [
        "Bea",
        "Ana",
    ]
    assert valores["orden"] == ""


def test_busqueda_vacia_no_filtra_resultados(app):
    crear_usuario_listado("a@example.com", "Ana")
    crear_usuario_listado("b@example.com", "Bea")
    consulta, valores = preparar_listado(
        db.select(Usuario),
        MultiDict({"q": "  "}),
        [Usuario.nombre],
        {},
        Usuario.nombre.asc(),
    )

    assert len(db.session.scalars(consulta).all()) == 2
    assert valores["q"] == ""


def test_orden_por_defecto_admite_varias_clausulas(app):
    crear_usuario_listado("a@example.com", "Ana")
    crear_usuario_listado("b@example.com", "Bea")
    predeterminado = [
        case((Usuario.nombre == "Bea", 0), else_=1),
        Usuario.nombre.desc(),
    ]
    consulta, _ = preparar_listado(
        db.select(Usuario),
        MultiDict(),
        [],
        {},
        predeterminado,
    )

    assert [usuario.nombre for usuario in db.session.scalars(consulta)] == [
        "Bea",
        "Ana",
    ]


def test_paginacion_corrige_valores_invalidos_y_fuera_de_rango(app):
    for numero in range(5):
        crear_usuario_listado(
            f"{numero}@example.com",
            f"Persona {numero}",
        )
    consulta = db.select(Usuario).order_by(Usuario.nombre)

    assert paginar_consulta(consulta, None, 2).page == 1
    assert paginar_consulta(consulta, "texto", 2).page == 1
    assert paginar_consulta(consulta, "0", 2).page == 1
    assert paginar_consulta(consulta, "-2", 2).page == 1
    assert paginar_consulta(consulta, "99", 2).page == 3


def test_paginacion_vacia_vuelve_a_la_primera_pagina(app):
    resultado = paginar_consulta(db.select(Usuario), "8", 2)

    assert resultado.page == 1
    assert resultado.pages == 0


def crear_noticia_listado(autor, titulo):
    noticia = Noticia(
        titulo=titulo,
        contenido="Contenido de prueba",
        autor=autor,
    )
    db.session.add(noticia)
    db.session.commit()
    return noticia


def test_listado_normaliza_pagina_por_defecto_invalida_y_fuera_de_rango(
    app, cliente, crear_usuario
):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    app.config["POR_PAGINA"] = 2
    for numero in range(3):
        crear_noticia_listado(socio, f"Noticia {numero}")
    with cliente.session_transaction() as sesion:
        sesion["_user_id"] = str(socio.id)
        sesion["_fresh"] = True

    casos = (
        (None, "Página 1 de 2"),
        ("texto", "Página 1 de 2"),
        ("0", "Página 1 de 2"),
        ("-1", "Página 1 de 2"),
        ("99", "Página 2 de 2"),
        ("9" * 100, "Página 2 de 2"),
    )
    for pagina, etiqueta in casos:
        ruta = "/noticias/" if pagina is None else f"/noticias/?pagina={pagina}"
        respuesta = cliente.get(ruta)
        assert etiqueta.encode() in respuesta.data


def test_paginacion_no_muestra_controles_en_una_sola_pagina(
    app, cliente, crear_usuario
):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    crear_noticia_listado(socio, "Única noticia")
    with cliente.session_transaction() as sesion:
        sesion["_user_id"] = str(socio.id)
        sesion["_fresh"] = True

    respuesta = cliente.get("/noticias/")

    assert b'aria-label="Paginaci\xc3\xb3n"' not in respuesta.data


def test_enlace_paginacion_conserva_busqueda_orden_y_filtro(
    app, cliente, crear_usuario
):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    app.config["POR_PAGINA"] = 1
    for titulo in ("Acta uno", "Acta dos"):
        db.session.add(
            Documento(
                titulo=titulo,
                descripcion="Documento para paginar",
                categoria="acta",
                nombre_original="acta.pdf",
                nombre_archivo=f"{titulo}.pdf",
                subido_por=socio,
            )
        )
    db.session.commit()
    with cliente.session_transaction() as sesion:
        sesion["_user_id"] = str(socio.id)
        sesion["_fresh"] = True

    respuesta = cliente.get(
        "/documentos/?q=Acta&orden=titulo&dir=asc&categoria=acta"
    )
    enlace = re.search(rb'href="([^"]+)">Siguiente', respuesta.data)
    assert enlace is not None
    parametros = parse_qs(
        urlsplit(html.unescape(enlace.group(1).decode())).query
    )

    assert parametros["pagina"] == ["2"]
    assert parametros["q"] == ["Acta"]
    assert parametros["orden"] == ["titulo"]
    assert parametros["dir"] == ["asc"]
    assert parametros["categoria"] == ["acta"]


def test_panel_filtros_cerrado_sin_ordenes_ni_filtros(
    cliente, crear_usuario
):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    with cliente.session_transaction() as sesion:
        sesion["_user_id"] = str(socio.id)
        sesion["_fresh"] = True

    respuesta = cliente.get("/noticias/?q=busqueda")

    assert respuesta.status_code == 200
    assert b'<details class="filtros">' in respuesta.data
    assert b"Filtros y orden (0)" in respuesta.data
    assert b'name="q" value="busqueda"' in respuesta.data
    assert b'>Buscar</button>' in respuesta.data


def test_panel_filtros_cuenta_orden_direccion_y_filtros_sin_busqueda(
    cliente, crear_usuario
):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    with cliente.session_transaction() as sesion:
        sesion["_user_id"] = str(socio.id)
        sesion["_fresh"] = True

    respuesta_noticias = cliente.get(
        "/noticias/?q=busqueda&orden=titulo&dir=asc"
    )
    assert b'<details class="filtros" open>' in respuesta_noticias.data
    assert b"Filtros y orden (2)" in respuesta_noticias.data

    respuesta_talleres = cliente.get(
        "/talleres/?q=busqueda&plazas_libres=si"
    )
    assert b'<details class="filtros" open>' in respuesta_talleres.data
    assert b"Filtros y orden (1)" in respuesta_talleres.data
    assert b'name="plazas_libres"' in respuesta_talleres.data


def test_panel_filtros_no_cuenta_el_anio_actual_predeterminado(
    cliente, crear_usuario
):
    administrador = crear_usuario(
        email="admin@example.com",
        rol="administrador",
        estado="activo",
    )
    db.session.add(
        Movimiento(
            tipo="ingreso",
            concepto="Movimiento de otro año",
            importe=Decimal("1.00"),
            fecha=date(2025, 1, 1),
        )
    )
    db.session.commit()
    with cliente.session_transaction() as sesion:
        sesion["_user_id"] = str(administrador.id)
        sesion["_fresh"] = True

    respuesta = cliente.get(
        f"/finanzas/movimientos?anio={date.today().year}"
    )

    assert respuesta.status_code == 200
    assert b'<details class="filtros">' in respuesta.data
    assert b"Filtros y orden (0)" in respuesta.data

    respuesta_otro_anio = cliente.get("/finanzas/movimientos?anio=2025")

    assert b'<details class="filtros" open>' in respuesta_otro_anio.data
    assert b"Filtros y orden (1)" in respuesta_otro_anio.data
