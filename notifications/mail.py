import logging
import smtplib
from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


class MailDeliveryError(Exception):
    retryable = True


class PermanentMailDeliveryError(MailDeliveryError):
    retryable = False


def _html_template(text_template):
    candidate = str(Path(text_template).with_suffix(".html"))
    return candidate


def deliver(payload, *, connection=None):
    text_body = render_to_string(payload["template"], payload["context"])
    html_body = render_to_string(_html_template(payload["template"]), payload["context"])
    message = EmailMultiAlternatives(
        subject=payload["subject"],
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[payload["to"]],
        connection=connection or get_connection(),
    )
    message.attach_alternative(html_body, "text/html")
    try:
        sent = message.send(fail_silently=False)
    except smtplib.SMTPResponseException as error:
        exception_class = MailDeliveryError if 400 <= error.smtp_code < 500 else PermanentMailDeliveryError
        raise exception_class(f"SMTP rejected the message with status {error.smtp_code}") from error
    except (smtplib.SMTPServerDisconnected, TimeoutError, OSError) as error:
        raise MailDeliveryError("SMTP delivery is temporarily unavailable") from error
    if sent != 1:
        raise MailDeliveryError("SMTP did not confirm delivery")
    logger.info(
        "email_delivered",
        extra={"event": "email_delivered", "email_template": payload["template"]},
    )
