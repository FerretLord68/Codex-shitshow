import getpass

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import User
from audit.services import audit_event


class Command(BaseCommand):
    help = "Interactively create the first administrator. Refuses to run after one exists."

    def add_arguments(self, parser):
        parser.add_argument("--email")

    def handle(self, *args, **options):
        if User.objects.filter(is_superuser=True).exists():
            raise CommandError("Administrator bootstrap is already complete.")
        email = options["email"] or input("Administrator e-mail: ").strip()
        password = getpass.getpass("Strong password: ")
        confirmation = getpass.getpass("Confirm password: ")
        if password != confirmation:
            raise CommandError("Passwords do not match.")
        candidate = User(email=email, display_name="Administrator")
        try:
            validate_password(password, candidate)
        except ValidationError as error:
            raise CommandError(" ".join(error.messages)) from error
        with transaction.atomic():
            user = User.objects.create_superuser(email=email, password=password, display_name="Administrator")
            audit_event("administrator.created", actor=user, metadata={"method": "bootstrap_admin"})
        self.stdout.write(self.style.SUCCESS(f"Administrator created for {email}."))

