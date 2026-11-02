from decimal import Decimal
from django import template

register = template.Library()


@register.filter(name="clp")
def clp(value):
    """Formatea un número 14510630 -> $14.510.630"""
    if value is None or value == "":
        return "$0"
    try:
        val = int(round(float(value)))
        return f"${val:,}".replace(",", ".")
    except (ValueError, TypeError):
        return f"${value}"


@register.filter(name="puntos")
def puntos(value):
    """Formatea un número con separador de miles con punto sin signo de peso:

    14510630 -> 14.510.630
    """
    if value is None or value == "":
        return "0"
    try:
        val = int(round(float(value)))
        return f"{val:,}".replace(",", ".")
    except (ValueError, TypeError):
        return f"{value}"
