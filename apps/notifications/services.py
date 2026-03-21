from django.core.mail import EmailMultiAlternatives
from django.conf import settings

def send_notification_email(subject, plain_message, recipient_email, html_message=None):
    email = EmailMultiAlternatives(
        subject=subject,
        body=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient_email],
    )
    if html_message:
        email.attach_alternative(html_message, "text/html")
    email.send()