from django import template

register = template.Library()

@register.filter
def contamination_to_percentage(value):
    """
    Convert contamination parameter (0.01-0.50) to percentage (1%-50%)
    """
    if value is None:
        return "0"
    try:
        percentage = float(value) * 100
        return f"{percentage:.0f}"
    except (ValueError, TypeError):
        return "0"

@register.filter
def multiply(value, arg):
    """
    Multiply the value by the argument
    """
    if value is None:
        return 0
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def abs_multiply(value, arg):
    """
    Take absolute value and multiply by argument
    """
    if value is None:
        return 0
    try:
        return abs(float(value)) * float(arg)
    except (ValueError, TypeError):
        return 0 