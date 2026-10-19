"""Pruebas del acceso administrativo y de la revisión de altas.

Verifican permisos, cambios de estado y su efecto sobre el inicio de sesión.
"""

from datetime import datetime, timezone

import pytest
from flask import g

from app.extensiones import db
from app.models import Documento, Inscripcion, Noticia, Taller, Usuario


def iniciar_sesion(cliente, usuario):
    with cliente.session_transaction() as sesion:
        sesion["_user_id"] = str(usuario.id)
        sesion["_fresh"] = True


def test_socio_recibe_403_en_lista_de_altas(app, cliente, crear_usuario):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    iniciar_sesion(cliente, socio)

    respuesta = cliente.get("/admin/altas")

    assert respuesta.status_code == 403


def test_sin_sesion_se_redirige_al_login(cliente):
    respuesta = cliente.get("/admin/altas")

    assert respuesta.status_code == 302
    assert "/auth/login?next=/admin/altas" in respuesta.headers["Location"]


def test_administrador_ve_solicitudes_pendientes(cliente, crear_usuario):
    administradora = crear_usuario(
        email="admin@example.com", rol="administrador", estado="activo"
    )
    pendiente = crear_usuario(
        email="pendiente@example.com", estado="pendiente"
    )
    iniciar_sesion(cliente, administradora)

    respuesta = cliente.get("/admin/altas")

    assert respuesta.status_code == 200
    assert b"pendiente@example.com" in respuesta.data
    assert b"Aprobar" in respuesta.data
    assert b"Rechazar" in respuesta.data
    assert pendiente.estado == "pendiente"


def test_aprobar_activa_usuario_y_permita_iniciar_sesion(
    app, cliente, crear_usuario
):
    administradora = crear_usuario(
        email="admin@example.com", rol="administrador", estado="activo"
    )
    pendiente = crear_usuario(
        email="pendiente@example.com", estado="pendiente"
    )
    iniciar_sesion(cliente, administradora)

    respuesta = cliente.post(f"/admin/altas/{pendiente.id}/aprobar")

    assert respuesta.status_code == 302
    assert db.session.get(Usuario, pendiente.id).estado == "activo"

    cliente_socio = app.test_client()
    respuesta_login = cliente_socio.post(
        "/auth/login",
        data={
            "email": "pendiente@example.com",
            "password": "clave-segura-123",
        },
    )
    assert respuesta_login.status_code == 302
    assert b"Hola, Ana" in cliente_socio.get("/auth/inicio").data


def test_rechazar_no_permite_iniciar_sesion(cliente, crear_usuario):
    administradora = crear_usuario(
        email="admin@example.com", rol="administrador", estado="activo"
    )
    pendiente = crear_usuario(
        email="pendiente@example.com", estado="pendiente"
    )
    iniciar_sesion(cliente, administradora)

    respuesta = cliente.post(f"/admin/altas/{pendiente.id}/rechazar")

    assert respuesta.status_code == 302
    assert db.session.get(Usuario, pendiente.id).estado == "rechazado"

    cliente.post("/auth/logout")
    respuesta_login = cliente.post(
        "/auth/login",
        data={
            "email": "pendiente@example.com",
            "password": "clave-segura-123",
        },
        follow_redirects=True,
    )
    assert respuesta_login.status_code == 200
    assert "Tu solicitud de alta ha sido rechazada.".encode() in respuesta_login.data
    assert cliente.get("/auth/inicio").status_code == 302


def test_aprobar_usuario_no_pendiente_no_cambia_estado(cliente, crear_usuario):
    administradora = crear_usuario(
        email="admin@example.com", rol="administrador", estado="activo"
    )
    activo = crear_usuario(email="activo@example.com", estado="activo")
    iniciar_sesion(cliente, administradora)

    respuesta = cliente.post(f"/admin/altas/{activo.id}/aprobar", follow_redirects=True)

    assert respuesta.status_code == 200
    assert db.session.get(Usuario, activo.id).estado == "activo"
    assert "La solicitud ya no está pendiente.".encode() in respuesta.data


def test_alta_inexistente_responde_404(cliente, crear_usuario):
    administradora = crear_usuario(
        email="admin@example.com", rol="administrador", estado="activo"
    )
    iniciar_sesion(cliente, administradora)

    assert cliente.post("/admin/altas/999/aprobar").status_code == 404


def test_administrador_ve_usuarios_rechazados(cliente, crear_usuario):
    administradora = crear_usuario(
        email="admin@example.com", rol="administrador", estado="activo"
    )
    rechazado = crear_usuario(
        email="rechazado@example.com", estado="rechazado"
    )
    iniciar_sesion(cliente, administradora)

    respuesta = cliente.get("/admin/altas")

    assert respuesta.status_code == 200
    assert rechazado.email.encode() in respuesta.data
    assert b"Reconsiderar" in respuesta.data
    assert b"Eliminar definitivamente" in respuesta.data


def test_reconsiderar_devuelve_usuario_a_pendiente(cliente, crear_usuario):
    administradora = crear_usuario(
        email="admin@example.com", rol="administrador", estado="activo"
    )
    rechazado = crear_usuario(
        email="rechazado@example.com", estado="rechazado"
    )
    iniciar_sesion(cliente, administradora)

    respuesta = cliente.post(
        f"/admin/altas/{rechazado.id}/reconsiderar",
        follow_redirects=True,
    )

    assert db.session.get(Usuario, rechazado.id).estado == "pendiente"
    assert (
        f"/admin/altas/{rechazado.id}/reconsiderar".encode()
        not in respuesta.data
    )
    assert b"rechazado@example.com" in respuesta.data
    assert "vuelve a estar pendiente".encode() in respuesta.data


def test_reconsiderar_usuario_no_rechazado_no_cambia_estado(
    cliente, crear_usuario
):
    administradora = crear_usuario(
        email="admin@example.com", rol="administrador", estado="activo"
    )
    pendiente = crear_usuario(
        email="pendiente@example.com", estado="pendiente"
    )
    iniciar_sesion(cliente, administradora)

    respuesta = cliente.post(
        f"/admin/altas/{pendiente.id}/reconsiderar",
        follow_redirects=True,
    )

    assert db.session.get(Usuario, pendiente.id).estado == "pendiente"
    assert b"Solo se pueden reconsiderar usuarios rechazados." in respuesta.data


def test_eliminar_rechazado_sin_contenido_libera_el_correo(
    cliente, crear_usuario
):
    administradora = crear_usuario(
        email="admin@example.com", rol="administrador", estado="activo"
    )
    rechazado = crear_usuario(
        email="rechazado@example.com", estado="rechazado"
    )
    id_rechazado = rechazado.id
    iniciar_sesion(cliente, administradora)

    sin_confirmar = cliente.post(
        f"/admin/altas/{id_rechazado}/eliminar",
        follow_redirects=True,
    )
    assert db.session.get(Usuario, id_rechazado) is not None
    assert b"Confirma que deseas eliminar" in sin_confirmar.data

    respuesta = cliente.post(
        f"/admin/altas/{id_rechazado}/eliminar",
        data={"confirmar_borrado": "si"},
        follow_redirects=True,
    )

    assert db.session.get(Usuario, id_rechazado) is None
    usuario_nuevo = crear_usuario(email="rechazado@example.com")
    assert usuario_nuevo.id is not None
    assert b"eliminado definitivamente" in respuesta.data


def test_no_eliminar_rechazado_con_inscripcion_asociada(
    cliente, crear_usuario
):
    administradora = crear_usuario(
        email="admin@example.com", rol="administrador", estado="activo"
    )
    rechazado = crear_usuario(
        email="rechazado@example.com", estado="rechazado"
    )
    taller = Taller(
        titulo="Taller de prueba",
        descripcion="Actividad",
        fecha_hora=datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc),
        lugar="Sala",
        plazas=5,
        creado_por=administradora,
    )
    db.session.add(taller)
    db.session.add(Inscripcion(taller=taller, usuario=rechazado))
    db.session.commit()
    iniciar_sesion(cliente, administradora)

    respuesta = cliente.post(
        f"/admin/altas/{rechazado.id}/eliminar",
        data={"confirmar_borrado": "si"},
        follow_redirects=True,
    )

    assert db.session.get(Usuario, rechazado.id) is not None
    assert "contenido asociado".encode() in respuesta.data


@pytest.mark.parametrize(
    ("estado", "rol"),
    [
        ("pendiente", "socio"),
        ("activo", "socio"),
        ("rechazado", "administrador"),
    ],
)
def test_eliminar_rechazado_rechaza_estado_o_rol_no_permitido(
    cliente, crear_usuario, estado, rol
):
    administradora = crear_usuario(
        email="admin@example.com", rol="administrador", estado="activo"
    )
    usuario = crear_usuario(
        email="usuario@example.com", estado=estado, rol=rol
    )
    iniciar_sesion(cliente, administradora)

    respuesta = cliente.post(
        f"/admin/altas/{usuario.id}/eliminar",
        data={"confirmar_borrado": "si"},
        follow_redirects=True,
    )

    assert db.session.get(Usuario, usuario.id) is not None
    if rol == "administrador":
        assert b"cuentas de administrador" in respuesta.data
    else:
        assert b"Solo se pueden eliminar usuarios rechazados." in respuesta.data


def test_administrador_no_puede_eliminarse_a_si_mismo(
    cliente, crear_usuario
):
    administradora = crear_usuario(
        email="admin@example.com", rol="administrador", estado="activo"
    )
    iniciar_sesion(cliente, administradora)

    respuesta = cliente.post(
        f"/admin/altas/{administradora.id}/eliminar",
        data={"confirmar_borrado": "si"},
        follow_redirects=True,
    )

    assert db.session.get(Usuario, administradora.id) is not None
    assert b"No puedes eliminar tu propia cuenta." in respuesta.data


def test_socio_y_anonimo_no_pueden_reconsiderar_ni_eliminar(
    app, cliente, crear_usuario
):
    administrador = crear_usuario(
        email="admin@example.com", rol="administrador", estado="activo"
    )
    rechazado = crear_usuario(
        email="rechazado@example.com", estado="rechazado"
    )
    iniciar_sesion(cliente, crear_usuario(email="socio@example.com", estado="activo"))
    rutas = (
        f"/admin/altas/{rechazado.id}/reconsiderar",
        f"/admin/altas/{rechazado.id}/eliminar",
    )

    for ruta in rutas:
        assert cliente.post(ruta).status_code == 403

    cliente_anonimo = app.test_client()
    for ruta in rutas:
        g.pop("_login_user", None)
        respuesta = cliente_anonimo.post(ruta)
        assert respuesta.status_code == 302
        assert "/auth/login" in respuesta.headers["Location"]
    assert db.session.get(Usuario, administrador.id) is not None
    assert db.session.get(Usuario, rechazado.id).estado == "rechazado"


def test_usuario_reconsiderado_puede_aprobarse_por_flujo_normal(
    cliente, crear_usuario
):
    administradora = crear_usuario(
        email="admin@example.com", rol="administrador", estado="activo"
    )
    usuario = crear_usuario(
        email="usuario@example.com", estado="rechazado"
    )
    iniciar_sesion(cliente, administradora)

    cliente.post(f"/admin/altas/{usuario.id}/reconsiderar")
    respuesta = cliente.post(
        f"/admin/altas/{usuario.id}/aprobar",
        follow_redirects=True,
    )

    assert db.session.get(Usuario, usuario.id).estado == "activo"
    assert b"Se ha aprobado el alta" in respuesta.data


def test_listado_general_muestra_usuarios_y_filtra_por_estado(
    cliente, crear_usuario
):
    administradora = crear_usuario(
        email="admin@example.com", rol="administrador", estado="activo"
    )
    usuarios = {
        estado: crear_usuario(
            email=f"{estado}@example.com",
            estado=estado,
        )
        for estado in ("pendiente", "activo", "rechazado", "baja")
    }
    iniciar_sesion(cliente, administradora)

    respuesta_todos = cliente.get("/admin/altas")
    assert all(usuario.email.encode() in respuesta_todos.data for usuario in usuarios.values())
    assert "Gestión de socios".encode() in respuesta_todos.data

    for estado, usuario in usuarios.items():
        respuesta_filtrada = cliente.get(f"/admin/altas?estado={estado}")
        assert usuario.email.encode() in respuesta_filtrada.data
        assert all(
            otro.email.encode() not in respuesta_filtrada.data
            for otro_estado, otro in usuarios.items()
            if otro_estado != estado
        )


def test_dar_de_baja_conserva_contenido_creado(
    cliente, crear_usuario
):
    administradora = crear_usuario(
        email="admin@example.com", rol="administrador", estado="activo"
    )
    socio = crear_usuario(email="socio@example.com", estado="activo")
    noticia = Noticia(
        titulo="Noticia del socio",
        contenido="Contenido conservado",
        autor=socio,
    )
    documento = Documento(
        titulo="Acta del socio",
        descripcion="Descripción",
        categoria="acta",
        nombre_original="acta.pdf",
        nombre_archivo="archivo-unico.pdf",
        subido_por=socio,
    )
    taller_creado = Taller(
        titulo="Taller creado por el socio",
        descripcion="Actividad",
        fecha_hora=datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc),
        lugar="Sala",
        plazas=5,
        creado_por=socio,
    )
    db.session.add_all([noticia, documento, taller_creado])
    db.session.commit()
    iniciar_sesion(cliente, administradora)

    respuesta = cliente.post(
        f"/admin/usuarios/{socio.id}/dar-baja",
        data={"confirmar_baja": "si"},
        follow_redirects=True,
    )

    assert db.session.get(Usuario, socio.id).estado == "baja"
    assert db.session.get(Noticia, noticia.id).autor_id == socio.id
    assert db.session.get(Documento, documento.id).subido_por_id == socio.id
    assert db.session.get(Taller, taller_creado.id).creado_por_id == socio.id
    assert b"Se ha dado de baja" in respuesta.data


def test_baja_cancela_inscripciones_futuras_y_conserva_historicas(
    cliente, crear_usuario
):
    administradora = crear_usuario(
        email="admin@example.com", rol="administrador", estado="activo"
    )
    socio = crear_usuario(email="socio@example.com", estado="activo")
    taller_futuro = Taller(
        titulo="Taller futuro",
        descripcion="Actividad",
        fecha_hora=datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc),
        lugar="Sala",
        plazas=1,
        creado_por=administradora,
    )
    taller_pasado = Taller(
        titulo="Taller pasado",
        descripcion="Actividad",
        fecha_hora=datetime(2020, 1, 1, 12, 0, tzinfo=timezone.utc),
        lugar="Sala",
        plazas=1,
        creado_por=administradora,
    )
    db.session.add_all([taller_futuro, taller_pasado])
    db.session.flush()
    inscripcion_futura = Inscripcion(taller=taller_futuro, usuario=socio)
    inscripcion_pasada = Inscripcion(taller=taller_pasado, usuario=socio)
    db.session.add_all([inscripcion_futura, inscripcion_pasada])
    db.session.commit()
    id_inscripcion_futura = inscripcion_futura.id
    id_inscripcion_pasada = inscripcion_pasada.id
    iniciar_sesion(cliente, administradora)

    cliente.post(
        f"/admin/usuarios/{socio.id}/dar-baja",
        data={"confirmar_baja": "si"},
    )

    assert db.session.get(Inscripcion, id_inscripcion_futura) is None
    assert db.session.get(Inscripcion, id_inscripcion_pasada) is not None
    assert taller_futuro.plazas_libres == 1
    assert taller_pasado.plazas_libres == 0


def test_reactivar_usuario_de_baja_permite_iniciar_sesion(
    app, cliente, crear_usuario
):
    administradora = crear_usuario(
        email="admin@example.com", rol="administrador", estado="activo"
    )
    usuario = crear_usuario(email="baja@example.com", estado="baja")
    iniciar_sesion(cliente, administradora)

    respuesta = cliente.post(
        f"/admin/usuarios/{usuario.id}/reactivar",
        follow_redirects=True,
    )
    cliente_socio = app.test_client()
    respuesta_login = cliente_socio.post(
        "/auth/login",
        data={"email": usuario.email, "password": "clave-segura-123"},
    )

    assert db.session.get(Usuario, usuario.id).estado == "activo"
    assert b"Se ha reactivado" in respuesta.data
    assert respuesta_login.status_code == 302
    assert b"Hola, Ana" in cliente_socio.get("/auth/inicio").data


def test_reactivar_usuario_que_no_esta_de_baja_se_rechaza(
    cliente, crear_usuario
):
    administradora = crear_usuario(
        email="admin@example.com", rol="administrador", estado="activo"
    )
    activo = crear_usuario(email="activo@example.com", estado="activo")
    iniciar_sesion(cliente, administradora)

    respuesta = cliente.post(
        f"/admin/usuarios/{activo.id}/reactivar",
        follow_redirects=True,
    )

    assert db.session.get(Usuario, activo.id).estado == "activo"
    assert b"Solo se pueden reactivar usuarios que est\xc3\xa9n de baja." in respuesta.data


@pytest.mark.parametrize("estado", ["pendiente", "rechazado", "baja"])
def test_dar_de_baja_a_usuario_no_activo_se_rechaza(
    cliente, crear_usuario, estado
):
    administradora = crear_usuario(
        email="admin@example.com", rol="administrador", estado="activo"
    )
    usuario = crear_usuario(
        email=f"{estado}@example.com",
        estado=estado,
    )
    iniciar_sesion(cliente, administradora)

    respuesta = cliente.post(
        f"/admin/usuarios/{usuario.id}/dar-baja",
        data={"confirmar_baja": "si"},
        follow_redirects=True,
    )

    assert db.session.get(Usuario, usuario.id).estado == estado
    assert b"Solo se puede dar de baja a usuarios activos." in respuesta.data


def test_no_se_puede_dar_de_baja_a_si_mismo(cliente, crear_usuario):
    administradora = crear_usuario(
        email="admin@example.com", rol="administrador", estado="activo"
    )
    iniciar_sesion(cliente, administradora)

    respuesta = cliente.post(
        f"/admin/usuarios/{administradora.id}/dar-baja",
        data={"confirmar_baja": "si"},
        follow_redirects=True,
    )

    assert db.session.get(Usuario, administradora.id).estado == "activo"
    assert b"No puedes darte de baja a ti mismo." in respuesta.data


def test_administrador_puede_dar_de_baja_a_otro_si_queda_uno_activo(
    cliente, crear_usuario
):
    administradora = crear_usuario(
        email="admin@example.com", rol="administrador", estado="activo"
    )
    otro_administrador = crear_usuario(
        email="admin-dos@example.com",
        rol="administrador",
        estado="activo",
    )
    iniciar_sesion(cliente, administradora)

    respuesta = cliente.post(
        f"/admin/usuarios/{otro_administrador.id}/dar-baja",
        data={"confirmar_baja": "si"},
        follow_redirects=True,
    )

    assert db.session.get(Usuario, otro_administrador.id).estado == "baja"
    assert db.session.get(Usuario, administradora.id).estado == "activo"
    assert b"Se ha dado de baja" in respuesta.data


def test_no_dar_de_baja_al_ultimo_administrador_activo(
    cliente, crear_usuario, monkeypatch
):
    administradora = crear_usuario(
        email="admin@example.com", rol="administrador", estado="activo"
    )
    otro_administrador = crear_usuario(
        email="admin-dos@example.com",
        rol="administrador",
        estado="activo",
    )
    iniciar_sesion(cliente, administradora)
    monkeypatch.setattr(
        "app.blueprints.admin.routes._administradores_activos",
        lambda: 1,
    )

    respuesta = cliente.post(
        f"/admin/usuarios/{otro_administrador.id}/dar-baja",
        data={"confirmar_baja": "si"},
        follow_redirects=True,
    )

    assert db.session.get(Usuario, otro_administrador.id).estado == "activo"
    assert b"No se puede dar de baja al \xc3\xbaltimo administrador activo." in respuesta.data


def test_socio_y_anonimo_no_pueden_gestionar_ciclo_de_vida(
    app, cliente, crear_usuario
):
    socio = crear_usuario(email="socio@example.com", estado="activo")
    usuario_baja = crear_usuario(email="baja@example.com", estado="baja")
    rutas = (
        "/admin/altas",
        f"/admin/usuarios/{socio.id}/dar-baja",
        f"/admin/usuarios/{usuario_baja.id}/reactivar",
    )
    iniciar_sesion(cliente, socio)

    assert cliente.get(rutas[0]).status_code == 403
    assert cliente.post(
        rutas[1], data={"confirmar_baja": "si"}
    ).status_code == 403
    assert cliente.post(rutas[2]).status_code == 403

    cliente_anonimo = app.test_client()
    g.pop("_login_user", None)
    assert cliente_anonimo.get(rutas[0]).status_code == 302
    g.pop("_login_user", None)
    assert cliente_anonimo.post(
        rutas[1], data={"confirmar_baja": "si"}
    ).status_code == 302
    g.pop("_login_user", None)
    assert cliente_anonimo.post(rutas[2]).status_code == 302
