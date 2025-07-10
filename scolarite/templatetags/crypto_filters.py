from django import template
from scolarite.utils.crypto import chiffrer_param

register = template.Library()

@register.filter
def crypter_id(value):
    return chiffrer_param(str(value))
