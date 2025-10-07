from django import template

register = template.Library()

@register.filter
def is_in_group(user, group_name):
    """Retorna True si el usuario pertenece al grupo especificado."""
    return user.groups.filter(name=group_name).exists()
 
@register.filter
def moneda_ar(value):
    """Devuelve un número con separador de miles '.' y decimal ','"""
    try:
        value = float(value)
        entero, decimal = f"{value:,.2f}".split(".")
        entero = entero.replace(",", ".")
        return f"{entero},{decimal}"
    except:
        return value