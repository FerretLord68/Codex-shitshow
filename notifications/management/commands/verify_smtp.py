import getpass
import smtplib
import socket
import ssl

from django.conf import settings
from django.core.mail import get_connection
from django.core.management.base import BaseCommand, CommandError

from notifications.mail import deliver


class Command(BaseCommand):
    help = "Verify SMTP DNS, TCP, TLS, authentication, and optional delivery."

    def add_arguments(self, parser):
        parser.add_argument("--recipient")
        parser.add_argument("--send", action="store_true")

    def handle(self, *args, **options):
        if not settings.SMTP_HOST or not settings.SMTP_USERNAME:
            raise CommandError("SMTP host and username must be configured.")
        password = settings.SMTP_PASSWORD or getpass.getpass("SMTP password: ")
        addresses = sorted({item[4][0] for item in socket.getaddrinfo(settings.SMTP_HOST, settings.SMTP_PORT)})
        self.stdout.write(f"DNS: {settings.SMTP_HOST} -> {', '.join(addresses)}")
        connection = get_connection(password=password)
        context = connection.ssl_context
        try:
            if settings.SMTP_SECURE:
                client = smtplib.SMTP_SSL(
                    settings.SMTP_HOST,
                    settings.SMTP_PORT,
                    timeout=settings.SMTP_CONNECTION_TIMEOUT_MS / 1000,
                    context=context,
                )
            else:
                client = smtplib.SMTP(
                    settings.SMTP_HOST,
                    settings.SMTP_PORT,
                    timeout=settings.SMTP_CONNECTION_TIMEOUT_MS / 1000,
                )
            with client:
                client.ehlo()
                self.stdout.write("TCP: connected")
                if not settings.SMTP_SECURE:
                    client.starttls(context=context)
                    client.ehlo()
                self.stdout.write("TLS: certificate verified")
                client.login(settings.SMTP_USERNAME, password)
                self.stdout.write("Authentication: accepted")
        except (OSError, ssl.SSLError, smtplib.SMTPException) as error:
            raise CommandError(f"SMTP verification failed: {type(error).__name__}") from error

        recipient = options["recipient"]
        if options["send"] and not recipient:
            recipient = input("Test recipient (leave blank to skip): ").strip()
        if options["send"] and recipient:
            deliver({
                "to": recipient,
                "subject": "MealHouse SMTP verification",
                "template": "email/smtp_test.txt",
                "context": {},
            }, connection=connection)
            self.stdout.write(self.style.SUCCESS("Test message accepted by SMTP."))
        else:
            self.stdout.write(self.style.SUCCESS("SMTP verification succeeded; no message sent."))
