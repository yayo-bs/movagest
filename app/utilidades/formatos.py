"""Filtros Jinja para presentar importes y fechas de forma uniforme.
No modifican los valores almacenados ni los datos enviados por los formularios.
"""

from datetime import date, datetime


def formato_euros(importe):
    """Muestra un importe con separadores numéricos españoles y dos decimales."""
    importe_formateado = f"{importe:,.2f}"
    importe_formateado = (
        importe_formateado.replace(",", "\0")
        .replace(".", ",")
        .replace("\0", ".")
    )
    return f"{importe_formateado} €"


def formato_fecha(fecha):
    """Muestra las fechas y horas con el formato habitual en España."""
    if isinstance(fecha, datetime):
        return fecha.strftime("%d/%m/%Y %H:%M")
    if isinstance(fecha, date):
        return fecha.strftime("%d/%m/%Y")
    raise TypeError("La fecha debe ser un objeto date o datetime.")


def anio_actual():
    """Devuelve el año actual para los valores predeterminados de plantillas."""
    return date.today().year
