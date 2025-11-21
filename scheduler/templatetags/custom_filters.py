from django import template

register = template.Library()

@register.filter
def dict_get(d, key):
    return d.get(key, [])

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def split(value, sep=" "):
    """Splits a string by the given separator"""
    return value.split(sep)


@register.filter
def time_slot(sched):
    """Return the string 'HH:MM-HH:MM' for a schedule"""
    start = sched.time_start.strftime("%H:%M")
    end = sched.time_end.strftime("%H:%M")
    return f"{start}-{end}"

@register.filter
def get_item(dictionary, key):
    """
    Safely get a key from a dictionary.
    Returns None if dictionary is None or key not found.
    """
    if dictionary and hasattr(dictionary, 'get'):
        return dictionary.get(key)
    return None