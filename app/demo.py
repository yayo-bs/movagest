"""Carga datos ficticios para demostraciones y capturas de MovaGest.

Cada registro usa identificadores reservados para que el reinicio sea selectivo.
"""

import os
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from html import escape
from uuid import uuid4

import click
from flask import current_app
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy import inspect

from app.extensiones import db
from app.finanzas.operaciones import (
    anular_cuota,
    generar_cuotas,
    marcar_cuota_pagada,
)
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
from app.utilidades.actividad import registrar


MARCA_DEMO = "[DEMO] "
CONTRASENA_DEMO = "Danza-MovaDemo-2026!"

USUARIOS_DEMO = (
    {
        "email": "junta@demo.example.com",
        "nombre": "Lina",
        "apellidos": "Trazo Lunar",
        "rol": "administrador",
        "estado_final": "activo",
    },
    {
        "email": "coordinacion@demo.example.com",
        "nombre": "Vera",
        "apellidos": "Ritmo Naciente",
        "rol": "administrador",
        "estado_final": "activo",
    },
    {
        "email": "socia01@demo.example.com",
        "nombre": "Alma",
        "apellidos": "Giro Sereno",
        "rol": "socio",
        "estado_final": "activo",
    },
    {
        "email": "socia02@demo.example.com",
        "nombre": "Iria",
        "apellidos": "Paso de Bruma",
        "rol": "socio",
        "estado_final": "activo",
    },
    {
        "email": "socia03@demo.example.com",
        "nombre": "Nara",
        "apellidos": "Luz Errante",
        "rol": "socio",
        "estado_final": "activo",
    },
    {
        "email": "socia04@demo.example.com",
        "nombre": "Elia",
        "apellidos": "Viento Escénico",
        "rol": "socio",
        "estado_final": "activo",
    },
    {
        "email": "socia05@demo.example.com",
        "nombre": "Mara",
        "apellidos": "Eje de Agua",
        "rol": "socio",
        "estado_final": "activo",
    },
    {
        "email": "socia06@demo.example.com",
        "nombre": "Noa",
        "apellidos": "Pulso Abierto",
        "rol": "socio",
        "estado_final": "activo",
    },
    {
        "email": "solicitud01@demo.example.com",
        "nombre": "Cira",
        "apellidos": "Danza de Sal",
        "rol": "socio",
        "estado_final": "pendiente",
    },
    {
        "email": "solicitud02@demo.example.com",
        "nombre": "Ene",
        "apellidos": "Rama en Movimiento",
        "rol": "socio",
        "estado_final": "pendiente",
    },
    {
        "email": "rechazada@demo.example.com",
        "nombre": "Luma",
        "apellidos": "Cauce Quieto",
        "rol": "socio",
        "estado_final": "rechazado",
    },
    {
        "email": "baja@demo.example.com",
        "nombre": "Sira",
        "apellidos": "Eco del Patio",
        "rol": "socio",
        "estado_final": "baja",
    },
)

TITULOS_NOTICIAS = (
    "DEMO | Laboratorio de movimiento y espacio",
    "DEMO | Abierta la muestra de proceso",
    "DEMO | Nuevo horario de ensayo",
    "DEMO | Encuentro de danza en el barrio",
    "DEMO | La compañía inicia temporada",
)

TITULOS_DOCUMENTOS = (
    "DEMO | Acta de asamblea de invierno",
    "DEMO | Estatutos del colectivo",
    "DEMO | Calendario de ensayos",
    "DEMO | Normas de uso de la sala",
)

TITULOS_TALLERES = (
    "DEMO | Improvisación con espacio libre",
    "DEMO | Composición en dúos casi completo",
    "DEMO | Suelo y suspensión completo",
    "DEMO | Taller pasado de escucha corporal",
)

TITULOS_ASAMBLEAS = (
    "DEMO | Asamblea ordinaria próxima",
    "DEMO | Asamblea extraordinaria pasada",
)

CONCEPTOS_MOVIMIENTOS = (
    "DEMO | Alquiler mensual de sala",
    "DEMO | Subvención cultural municipal",
    "DEMO | Material para ensayo",
    "DEMO | Venta de entradas de muestra",
    "DEMO | Seguro de responsabilidad civil",
    "DEMO | Diseño de cartelera",
    "DEMO | Aportación de taller intensivo",
    "DEMO | Transporte de escenografía",
    "DEMO | Cuota de mantenimiento técnico",
    "DEMO | Taquilla de función de primavera",
)

CONTENIDOS_NOTICIAS = (
    "El laboratorio propone investigar el peso, la pausa y las trayectorias "
    "que aparecen al compartir la sala.",
    "El sábado abriremos el ensayo para mostrar fragmentos de la nueva pieza. "
    "La entrada es libre hasta completar el aforo.",
    "A partir de esta semana el grupo avanzado ensaya los martes y jueves. "
    "El grupo abierto mantiene su horario habitual.",
    "Nos reuniremos con otros colectivos para una práctica compartida y una "
    "conversación sobre creación comunitaria.",
    "Comenzamos una nueva etapa de trabajo con sesiones de investigación, "
    "montaje y devolución.\n\nLa primera muestra interna será a final de mes.",
)

DOCUMENTOS_DEMO = (
    (
        TITULOS_DOCUMENTOS[0],
        "acta",
        "Acuerdos de programación, cuidados y calendario de actividades.",
    ),
    (
        TITULOS_DOCUMENTOS[1],
        "documento",
        "Principios organizativos del colectivo ficticio Cuerpo en Tránsito.",
    ),
    (
        TITULOS_DOCUMENTOS[2],
        "documento",
        "Fechas de ensayo, laboratorios y muestras de la temporada.",
    ),
    (
        TITULOS_DOCUMENTOS[3],
        "documento",
        "Pautas compartidas para preparar y dejar la sala de ensayo.",
    ),
)

MOVIMIENTOS_DEMO = (
    ("gasto", Decimal("420.00"), "Alquiler de sala"),
    ("ingreso", Decimal("1200.00"), "Subvención cultural"),
    ("gasto", Decimal("86.50"), "Material de ensayo"),
    ("ingreso", Decimal("315.00"), "Venta de entradas"),
    ("gasto", Decimal("148.00"), "Seguro anual"),
    ("gasto", Decimal("65.00"), "Diseño de cartel"),
    ("ingreso", Decimal("240.00"), "Taller intensivo"),
    ("gasto", Decimal("92.00"), "Transporte de escenografía"),
    ("gasto", Decimal("54.00"), "Mantenimiento técnico"),
    ("ingreso", Decimal("510.00"), "Taquilla de primavera"),
)


def _datos_demo_completos():
    """Indica si una ejecución anterior terminó y registró su marca final."""
    return db.session.scalar(
        db.select(Actividad.id)
        .where(
            Actividad.accion == "demo.cargar",
            Actividad.descripcion.startswith(MARCA_DEMO),
        )
        .limit(1)
    ) is not None


def _comprobar_tablas():
    """Evita que la carga falle con un mensaje SQLAlchemy poco comprensible."""
    tablas_necesarias = set(db.Model.metadata.tables)
    tablas_existentes = set(inspect(db.engine).get_table_names())
    if not tablas_necesarias.issubset(tablas_existentes):
        raise click.ClickException(
            "Faltan tablas de la base de datos. Ejecuta primero "
            "`flask --app run.py init-db`."
        )


def _borrar_por_titulos(modelo, columna, titulos):
    """Elimina registros cuyo título está reservado para la demo."""
    consulta = db.select(modelo).where(columna.in_(titulos))
    for registro in db.session.scalars(consulta).all():
        db.session.delete(registro)


def _limpiar_datos_demo():
    """Borra solo filas marcadas y conserva cualquier dato no demo."""
    usuarios = db.session.scalars(
        db.select(Usuario).where(
            Usuario.email.in_([dato["email"] for dato in USUARIOS_DEMO])
        )
    ).all()
    ids_usuarios = [usuario.id for usuario in usuarios]

    talleres = db.session.scalars(
        db.select(Taller).where(Taller.titulo.in_(TITULOS_TALLERES))
    ).all()
    ids_talleres = [taller.id for taller in talleres]
    if ids_talleres:
        db.session.execute(
            db.delete(Inscripcion).where(
                Inscripcion.taller_id.in_(ids_talleres)
            )
        )
    for taller in talleres:
        db.session.delete(taller)

    documentos = db.session.scalars(
        db.select(Documento).where(Documento.titulo.in_(TITULOS_DOCUMENTOS))
    ).all()
    archivos_a_borrar = [
        documento.nombre_archivo for documento in documentos
    ]
    for documento in documentos:
        db.session.delete(documento)

    _borrar_por_titulos(Noticia, Noticia.titulo, TITULOS_NOTICIAS)
    _borrar_por_titulos(Asamblea, Asamblea.titulo, TITULOS_ASAMBLEAS)
    _borrar_por_titulos(
        Movimiento,
        Movimiento.concepto,
        CONCEPTOS_MOVIMIENTOS,
    )
    if ids_usuarios:
        db.session.execute(
            db.delete(Cuota).where(Cuota.usuario_id.in_(ids_usuarios))
        )
    db.session.execute(
        db.delete(Actividad).where(
            Actividad.descripcion.startswith(MARCA_DEMO)
        )
    )
    db.session.flush()
    return archivos_a_borrar


def _obtener_usuarios_demo(contadores):
    """Crea o restablece exclusivamente las cuentas con correo demo reservado."""
    usuarios = {}
    for indice, datos in enumerate(USUARIOS_DEMO):
        usuario = db.session.scalar(
            db.select(Usuario).where(Usuario.email == datos["email"])
        )
        if usuario is None:
            usuario = Usuario(email=datos["email"])
            db.session.add(usuario)
        contadores["usuarios"] += 1

        usuario.nombre = datos["nombre"]
        usuario.apellidos = datos["apellidos"]
        usuario.rol = datos["rol"]
        usuario.estado = "pendiente"
        usuario.establecer_password(CONTRASENA_DEMO)
        db.session.flush()

        if datos["estado_final"] == "activo":
            usuario.aprobar()
            _registrar_demo(
                "socio.aprobar",
                f"Aprobada el alta de {usuario.nombre} {usuario.apellidos}",
                usuario=_administrador_actual(usuarios, usuario),
            )
        elif datos["estado_final"] == "rechazado":
            usuario.rechazar()
        elif datos["estado_final"] == "baja":
            usuario.aprobar()
            usuario.dar_de_baja()

        if indice == 0:
            usuarios["administrador"] = usuario
        else:
            usuarios[datos["email"]] = usuario

    administrador = usuarios["administrador"]
    for usuario in usuarios.values():
        if usuario.estado == "rechazado":
            _registrar_demo(
                "socio.rechazar",
                f"Rechazada el alta de {usuario.nombre} {usuario.apellidos}",
                administrador,
            )
        elif usuario.estado == "baja":
            _registrar_demo(
                "socio.baja",
                f"Dada de baja {usuario.nombre} {usuario.apellidos}",
                administrador,
            )
    return usuarios


def _administrador_actual(usuarios, usuario):
    """Devuelve el primer administrador para atribuir sus propias acciones."""
    return usuarios.get("administrador", usuario)


def _registrar_demo(accion, descripcion, usuario):
    """Añade una acción demo claramente marcada al historial."""
    registrar(
        accion,
        f"{MARCA_DEMO}{descripcion}",
        usuario=usuario,
    )


def _crear_noticias(administrador, contadores):
    hoy = datetime.now(timezone.utc)
    for indice, titulo in enumerate(TITULOS_NOTICIAS):
        noticia = db.session.scalar(
            db.select(Noticia).where(Noticia.titulo == titulo)
        )
        if noticia is not None:
            continue
        noticia = Noticia(
            titulo=titulo,
            contenido=CONTENIDOS_NOTICIAS[indice],
            fecha_publicacion=hoy - timedelta(days=(indice + 1) * 9),
            autor=administrador,
        )
        db.session.add(noticia)
        _registrar_demo(
            "noticia.crear",
            f"Creada la noticia «{titulo}»",
            administrador,
        )
        contadores["noticias"] += 1


def _crear_pdf(titulo, contenido):
    """Genera un PDF pequeño en memoria y lo guarda con nombre UUID."""
    nombre_archivo = f"{uuid4().hex}.pdf"
    ruta_archivo = os.path.join(
        current_app.config["CARPETA_SUBIDAS"],
        nombre_archivo,
    )
    estilos = getSampleStyleSheet()
    documento_pdf = SimpleDocTemplate(
        ruta_archivo,
        pagesize=A4,
        rightMargin=22 * mm,
        leftMargin=22 * mm,
        topMargin=22 * mm,
        bottomMargin=22 * mm,
        title=titulo,
    )
    contenido_pdf = [
        Paragraph(escape(titulo), estilos["Title"]),
        Spacer(1, 8 * mm),
        Paragraph(escape(contenido), estilos["BodyText"]),
    ]
    documento_pdf.build(contenido_pdf)
    return nombre_archivo


def _crear_documentos(administrador, contadores, archivos_nuevos):
    """Guarda metadatos y archivos de los cuatro PDF de demostración."""
    os.makedirs(current_app.config["CARPETA_SUBIDAS"], exist_ok=True)
    for titulo, categoria, descripcion in DOCUMENTOS_DEMO:
        existente = db.session.scalar(
            db.select(Documento).where(Documento.titulo == titulo)
        )
        if existente is not None:
            continue

        nombre_archivo = _crear_pdf(titulo, descripcion)
        archivos_nuevos.append(nombre_archivo)
        db.session.add(
            Documento(
                titulo=titulo,
                descripcion=descripcion,
                categoria=categoria,
                nombre_original=f"{titulo.replace('DEMO | ', '', 1)}.pdf",
                nombre_archivo=nombre_archivo,
                subido_por=administrador,
            )
        )
        _registrar_demo(
            "documento.subir",
            f"Subido el archivo «{titulo}» ({categoria})",
            administrador,
        )
        contadores["documentos"] += 1


def _crear_talleres(administrador, socios, contadores):
    """Crea talleres futuros/pasados con inscripciones dentro del aforo."""
    ahora = datetime.now(timezone.utc)
    definiciones = (
        (7, 8, (0, 1)),
        (15, 4, (0, 1, 2)),
        (23, 4, (0, 1, 2, 3)),
        (-20, 6, (3, 4)),
    )
    talleres = []
    for indice, titulo in enumerate(TITULOS_TALLERES):
        taller = db.session.scalar(
            db.select(Taller).where(Taller.titulo == titulo)
        )
        if taller is None:
            dias, plazas, indices_socios = definiciones[indice]
            taller = Taller(
                titulo=titulo,
                descripcion=(
                    "Práctica de danza contemporánea centrada en la "
                    "escucha, la improvisación y la composición colectiva."
                ),
                fecha_hora=ahora + timedelta(days=dias),
                lugar="Sala Umbral, espacio ficticio de ensayo",
                plazas=plazas,
                creado_por=administrador,
            )
            db.session.add(taller)
            _registrar_demo(
                "taller.crear",
                f"Creado el taller «{titulo}»",
                administrador,
            )
            contadores["talleres"] += 1
            for indice_socio in indices_socios:
                db.session.add(
                    Inscripcion(
                        taller=taller,
                        usuario=socios[indice_socio],
                    )
                )
                contadores["inscripciones"] += 1
        talleres.append(taller)
    return talleres


def _crear_asambleas(administrador, contadores):
    """Crea una convocatoria futura y otra pasada con su orden del día."""
    ahora = datetime.now(timezone.utc)
    for indice, titulo in enumerate(TITULOS_ASAMBLEAS):
        existente = db.session.scalar(
            db.select(Asamblea).where(Asamblea.titulo == titulo)
        )
        if existente is not None:
            continue
        dias = 30 if indice == 0 else -35
        db.session.add(
            Asamblea(
                titulo=titulo,
                tipo="ordinaria" if indice == 0 else "extraordinaria",
                fecha_hora=ahora + timedelta(days=dias),
                lugar="Sala Umbral, espacio ficticio de ensayo",
                orden_del_dia=(
                    "1. Lectura y aprobación del acta anterior.\n"
                    "2. Calendario de ensayos y muestras.\n"
                    "3. Propuestas de colaboración y ruegos."
                ),
                autor=administrador,
            )
        )
        _registrar_demo(
            "asamblea.crear",
            f"Creada la convocatoria «{titulo}»",
            administrador,
        )
        contadores["asambleas"] += 1


def _crear_cuotas(administrador, socios, contadores):
    """Genera dos periodos y asigna recibos mediante la operación común."""
    hoy = date.today()
    periodos = (hoy.year - 1, hoy.year)
    for periodo in periodos:
        contadores["cuotas"] += generar_cuotas(
            periodo,
            Decimal("35.00"),
            socios=socios,
            usuario=administrador,
            marca=MARCA_DEMO,
        )

    cuotas_por_periodo = {
        periodo: {
            cuota.usuario.email: cuota
            for cuota in db.session.scalars(
                db.select(Cuota).where(Cuota.periodo == periodo)
            ).all()
            if cuota.usuario_id in {socio.id for socio in socios}
        }
        for periodo in periodos
    }

    for indice in range(4):
        cuota = cuotas_por_periodo[periodos[0]][socios[indice].email]
        marcar_cuota_pagada(
            cuota,
            hoy - timedelta(days=10 - indice),
            usuario=administrador,
            marca=MARCA_DEMO,
        )
    cuota_actual_pagada = cuotas_por_periodo[periodos[1]][socios[0].email]
    marcar_cuota_pagada(
        cuota_actual_pagada,
        hoy,
        usuario=administrador,
        marca=MARCA_DEMO,
    )
    cuota_anulada = cuotas_por_periodo[periodos[1]][socios[1].email]
    marcar_cuota_pagada(
        cuota_anulada,
        hoy,
        usuario=administrador,
        marca=MARCA_DEMO,
    )
    anular_cuota(cuota_anulada, usuario=administrador, marca=MARCA_DEMO)


def _crear_movimientos(administrador, contadores):
    """Registra diez movimientos distribuidos desde enero hasta hoy."""
    hoy = date.today()
    dias_desde_enero = (hoy - date(hoy.year, 1, 1)).days
    for indice, (tipo, importe, categoria) in enumerate(MOVIMIENTOS_DEMO):
        concepto = CONCEPTOS_MOVIMIENTOS[indice]
        existente = db.session.scalar(
            db.select(Movimiento).where(Movimiento.concepto == concepto)
        )
        if existente is not None:
            continue
        dias_antes = round(dias_desde_enero * (9 - indice) / 9)
        db.session.add(
            Movimiento(
                tipo=tipo,
                concepto=concepto,
                importe=importe,
                fecha=hoy - timedelta(days=dias_antes),
                categoria=categoria,
            )
        )
        _registrar_demo(
            "movimiento.crear",
            f"Creado el movimiento «{concepto}»",
            administrador,
        )
        contadores["movimientos"] += 1


def _guardar_archivos_eliminados(nombres):
    """Borra los PDF demo anteriores después de confirmar la transacción."""
    carpeta = current_app.config["CARPETA_SUBIDAS"]
    for nombre in nombres:
        if os.path.basename(nombre) != nombre:
            raise ValueError("El nombre de archivo demo no es válido.")
        ruta_archivo = os.path.join(carpeta, nombre)
        if os.path.isfile(ruta_archivo):
            os.remove(ruta_archivo)


def cargar_datos_demo(reiniciar=False):
    """Carga el conjunto ficticio sin alterar datos que no estén marcados."""
    _comprobar_tablas()
    if not reiniciar and _datos_demo_completos():
        return {tipo: 0 for tipo in _tipos_contadores()}

    contadores = {tipo: 0 for tipo in _tipos_contadores()}
    archivos_eliminados = []
    archivos_nuevos = []
    try:
        if reiniciar:
            archivos_eliminados = _limpiar_datos_demo()
        usuarios = _obtener_usuarios_demo(contadores)
        administrador = usuarios["administrador"]
        socios = [
            usuarios[f"socia{indice:02d}@demo.example.com"]
            for indice in range(1, 7)
        ]
        _crear_noticias(administrador, contadores)
        _crear_documentos(administrador, contadores, archivos_nuevos)
        _crear_talleres(administrador, socios, contadores)
        _crear_asambleas(administrador, contadores)
        _crear_cuotas(administrador, socios, contadores)
        _crear_movimientos(administrador, contadores)
        registrar(
            "demo.cargar",
            f"{MARCA_DEMO}Carga de datos completada.",
        )
        db.session.flush()
        contadores["actividad"] = db.session.scalar(
            db.select(db.func.count(Actividad.id)).where(
                Actividad.descripcion.startswith(MARCA_DEMO)
            )
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        for nombre in archivos_nuevos:
            ruta_archivo = os.path.join(
                current_app.config["CARPETA_SUBIDAS"],
                nombre,
            )
            if os.path.isfile(ruta_archivo):
                os.remove(ruta_archivo)
        raise

    _guardar_archivos_eliminados(archivos_eliminados)
    return contadores


def _tipos_contadores():
    """Nombres estables para el resumen del comando."""
    return (
        "usuarios",
        "noticias",
        "documentos",
        "talleres",
        "inscripciones",
        "asambleas",
        "cuotas",
        "movimientos",
        "actividad",
    )


@click.command("cargar-demo")
@click.option(
    "--reiniciar",
    is_flag=True,
    help="Borra únicamente los datos marcados como demo y los recrea.",
)
@click.option(
    "--forzar",
    is_flag=True,
    help="Permite cargar datos demo con configuración de producción.",
)
def comando_cargar_demo(reiniciar, forzar):
    """Crea contenido ficticio para probar y mostrar la aplicación."""
    if current_app.config.get("MODO_PRODUCCION") and not forzar:
        raise click.ClickException(
            "La carga de datos demo está bloqueada en producción. "
            "Usa --forzar solo si realmente lo necesitas."
        )

    contadores = cargar_datos_demo(reiniciar=reiniciar)
    click.echo("Resumen de datos creados:")
    for tipo, cantidad in contadores.items():
        click.echo(f"- {tipo.capitalize()}: {cantidad}")
    click.echo("Credenciales demo (contraseña común):")
    click.echo(f"- junta@demo.example.com / {CONTRASENA_DEMO}")
    click.echo(f"- coordinacion@demo.example.com / {CONTRASENA_DEMO}")
    click.echo(f"- socia01@demo.example.com / {CONTRASENA_DEMO}")
