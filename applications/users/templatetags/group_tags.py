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

@register.filter(name='add_attrs')
def add_attrs(field, attrs):
    """
    Agrega múltiples atributos a un campo de formulario.
    Ejemplo: {{ form.campo|add_attrs:"class:form-control,autocomplete:new-password" }}
    """
    attrs_dict = {}
    for attr in attrs.split(','):
        if ':' in attr:
            key, value = attr.split(':', 1)
            attrs_dict[key.strip()] = value.strip()
    return field.as_widget(attrs=attrs_dict)