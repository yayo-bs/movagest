"""Generación en memoria de recibos de cuota en formato PDF.

El archivo devuelto se entrega directamente al navegador sin guardarlo en disco.
"""

from decimal import Decimal
from html import escape
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def formatear_importe_espanol(importe):
    """Formatea un importe Decimal con separadores numéricos españoles."""
    if not isinstance(importe, Decimal):
        raise TypeError("El importe debe ser un valor Decimal.")
    importe_formateado = f"{importe:,.2f}"
    importe_formateado = (
        importe_formateado.replace(",", "\0")
        .replace(".", ",")
        .replace("\0", ".")
    )
    return f"{importe_formateado} €"


def generar_recibo_pdf(cuota, nombre_asociacion="MovaGest"):
    """Devuelve el recibo de una cuota como un flujo BytesIO."""
    archivo = BytesIO()
    documento = SimpleDocTemplate(
        archivo,
        pagesize=A4,
        rightMargin=25 * mm,
        leftMargin=25 * mm,
        topMargin=25 * mm,
        bottomMargin=25 * mm,
        title=f"Recibo {cuota.numero_recibo}",
    )
    estilos = getSampleStyleSheet()
    contenido = [
        Paragraph(escape(nombre_asociacion), estilos["Title"]),
        Spacer(1, 12 * mm),
        Paragraph(
            f"<b>Número de recibo:</b> {escape(cuota.numero_recibo)}",
            estilos["BodyText"],
        ),
        Spacer(1, 4 * mm),
        Paragraph(
            f"<b>Fecha de pago:</b> {cuota.fecha_pago.strftime('%d/%m/%Y')}",
            estilos["BodyText"],
        ),
        Spacer(1, 4 * mm),
        Paragraph(
            f"<b>Socio:</b> {escape(cuota.usuario.nombre or '')} "
            f"{escape(cuota.usuario.apellidos or '')}",
            estilos["BodyText"],
        ),
        Spacer(1, 4 * mm),
        Paragraph(
            f"<b>Correo electrónico:</b> {escape(cuota.usuario.email)}",
            estilos["BodyText"],
        ),
        Spacer(1, 8 * mm),
        Paragraph(
            f"Cuota de socio &#8212; periodo {cuota.periodo}",
            estilos["Heading2"],
        ),
        Spacer(1, 4 * mm),
        Paragraph(
            f"<b>Importe:</b> {escape(formatear_importe_espanol(cuota.importe))}",
            estilos["BodyText"],
        ),
        Spacer(1, 18 * mm),
        Paragraph(
            "Recibo de cuota; no constituye factura con validez fiscal",
            estilos["BodyText"],
        ),
    ]
    estilos["Title"].textColor = colors.HexColor("#243447")
    documento.build(contenido)
    archivo.seek(0)
    return archivo
