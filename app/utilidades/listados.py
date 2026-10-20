"""Funciones comunes para buscar, ordenar, filtrar y paginar consultas.

Las ordenaciones y filtros se reciben como listas blancas definidas por cada módulo.
"""

import sys

from sqlalchemy import or_

from app.extensiones import db


def preparar_listado(
    consulta,
    parametros,
    campos_busqueda,
    ordenaciones,
    orden_por_defecto,
    filtros=None,
    direccion_por_defecto="desc",
):
    """Aplica búsqueda, orden y filtros permitidos a una consulta SQLAlchemy.

    El orden por defecto puede ser una cláusula o una lista de cláusulas
    ``order_by``. Esa lista permite definir órdenes compuestos en SQL.
    """
    valores = {
        "q": parametros.get("q", "").strip(),
        "orden": "",
        "dir": parametros.get("dir", direccion_por_defecto),
    }
    if valores["dir"] not in ("asc", "desc"):
        valores["dir"] = direccion_por_defecto

    if valores["q"]:
        texto = (
            valores["q"]
            .replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )
        expresion = f"%{texto}%"
        consulta = consulta.where(
            or_(
                *(
                    campo.ilike(expresion, escape="\\")
                    for campo in campos_busqueda
                )
            )
        )

    orden = parametros.get("orden", "")
    if orden in ordenaciones:
        valores["orden"] = orden
        columna = ordenaciones[orden]
        clausula = columna.asc() if valores["dir"] == "asc" else columna.desc()
        consulta = consulta.order_by(None).order_by(clausula)
    else:
        if isinstance(orden_por_defecto, (list, tuple)):
            clausulas = orden_por_defecto
        else:
            clausulas = (orden_por_defecto,)
        consulta = consulta.order_by(None).order_by(*clausulas)

    for nombre, opciones in (filtros or {}).items():
        valor = parametros.get(nombre, "")
        clausula = opciones.get(valor)
        if clausula is not None:
            consulta = consulta.where(clausula)
            valores[nombre] = valor
        else:
            valores[nombre] = ""

    return consulta, valores


def paginar_consulta(consulta, pagina, por_pagina):
    """Devuelve una página sin error para números inválidos o fuera de rango."""
    try:
        numero_pagina = int(pagina)
    except (TypeError, ValueError):
        numero_pagina = 1
    if numero_pagina < 1:
        numero_pagina = 1
    numero_pagina = min(
        numero_pagina,
        sys.maxsize // por_pagina + 1,
    )

    resultado = db.paginate(
        consulta,
        page=numero_pagina,
        per_page=por_pagina,
        error_out=False,
    )
    if resultado.pages == 0 and numero_pagina != 1:
        resultado = db.paginate(
            consulta,
            page=1,
            per_page=por_pagina,
            error_out=False,
        )
    elif resultado.pages and numero_pagina > resultado.pages:
        resultado = db.paginate(
            consulta,
            page=resultado.pages,
            per_page=por_pagina,
            error_out=False,
        )
    return resultado
