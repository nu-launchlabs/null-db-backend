import logging
import smtplib
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

logger = logging.getLogger(__name__)

def send_notification_email(subject, plain_message, recipient_email, html_message=None):
    email = EmailMultiAlternatives(
        subject=subject,
        body=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient_email],
    )
    if html_message:
        email.attach_alternative(html_message, "text/html")

    try:
        email.send()
    except smtplib.SMTPRecipientsRefused:
        logger.error("Email rejected for recipient %s -- bad address", recipient_email)
        raise
    except smtplib.SMTPException:
        logger.exception("Failed to send email to recipient %s", recipient_email)
        raise
