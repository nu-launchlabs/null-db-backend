
import smtplib
import pytest
from unittest.mock import MagicMock, patch
from django.conf import settings
from apps.notifications.services import send_notification_email


@patch("apps.notifications.services.EmailMultiAlternatives")
def test_send_correct_fields_no_html(mock_email_class):
    mock_instance = MagicMock()
    mock_email_class.return_value = mock_instance

    send_notification_email(
        subject="Test Subject",
        plain_message="Hello",
        recipient_email="test@example.com",
    )

    mock_email_class.assert_called_once_with(
        subject="Test Subject",
        body="Hello",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=["test@example.com"],
    )

    mock_instance.attach_alternative.assert_not_called()
    mock_instance.send.assert_called_once_with()

@patch("apps.notifications.services.EmailMultiAlternatives")
def test_send_correct_fields_with_html(mock_email_class):
    mock_instance = MagicMock()
    mock_email_class.return_value = mock_instance

    send_notification_email(
        subject="Test Subject",
        plain_message="Hello",
        html_message="<p>Hello</p>",
        recipient_email="test@example.com",
    )

    mock_email_class.assert_called_once_with(
        subject="Test Subject",
        body="Hello",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=["test@example.com"]
    )

    mock_instance.attach_alternative.assert_called_once_with("<p>Hello</p>", "text/html")
    mock_instance.send.assert_called_once_with()

@patch("apps.notifications.services.EmailMultiAlternatives")
def test_smtp_recipients_refused(mock_email_class):
    mock_instance = MagicMock()
    mock_email_class.return_value = mock_instance
    mock_instance.send.side_effect = smtplib.SMTPRecipientsRefused(recipients={})

    with pytest.raises(smtplib.SMTPRecipientsRefused):
        send_notification_email(
            subject="Test Subject",
            plain_message="Hello",
            recipient_email="test@example.com"
        )

@patch("apps.notifications.services.EmailMultiAlternatives")
def test_smtp_exception(mock_email_class):
    mock_instance = MagicMock()
    mock_email_class.return_value = mock_instance
    mock_instance.send.side_effect = smtplib.SMTPException()

    with pytest.raises(smtplib.SMTPException):
        send_notification_email(
            subject="Test Subject",
            plain_message="Hello",
            recipient_email="test@example.com"
        )