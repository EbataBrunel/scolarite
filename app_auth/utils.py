import logging

from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import send_mail



logger = logging.getLogger(__name__)


def send_email_with_html_body(subject: str, receivers: list, template:str, context: dict):
    #Cette fonction permet d'envoyer un e-mail personnalisé à un utilisateur ou à un ensemble d'utilisateurs spécifique
    try:
        message = render_to_string(template, context)

        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            receivers,
            fail_silently=True,
            html_message=message
        )

        return True

    except Exception as e:
        logger.error(e)

    return False