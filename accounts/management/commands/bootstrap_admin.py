import getpass

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import User
from audit.services import audit_event


class Command(BaseCommand):
    help = "Interactively create or upgrade the first administrator."

    def add_arguments(self, parser):
        parser.add_argument("--email", default="frederikjuulolsen@gmail.com")

    def handle(self, *args, **options):
        if User.objects.filter(is_superuser=True).exists():
            raise CommandError("Administrator bootstrap is already complete.")
        default_email = options["email"]
        entered = input(f"Administrator e-mail [{default_email}]: ").strip()
        email = User.objects.normalize_email(entered or default_email).strip().lower()
        existing = User.objects.filter(email=email).first()
        candidate = existing or User(email=email, username=email, display_name="Administrator")
        if not existing:
            try:
                candidate.full_clean(exclude=["password"])
            except ValidationError as error:
                raise CommandError(" ".join(error.messages)) from error
        if existing:
            answer = input("A normal user exists for this address. Upgrade it to administrator? [y/N]: ")
            if answer.strip().lower() not in {"y", "yes"}:
                raise CommandError("Administrator bootstrap cancelled.")
        password = getpass.getpass("Strong password: ")
        confirmation = getpass.getpass("Confirm password: ")
        if password != confirmation:
            raise CommandError("Passwords do not match.")
        try:
            validate_password(password, candidate)
        except ValidationError as error:
            raise CommandError(" ".join(error.messages)) from error
        with transaction.atomic():
            user = User.objects.select_for_update().filter(email=email).first()
            if user:
                user.is_staff = True
                user.is_superuser = True
                user.is_active = True
                user.is_suspended = False
                user.is_email_verified = True
                user.set_password(password)
                user.save()
                event = "administrator.upgraded"
                action = "upgraded"
            else:
                user = User.objects.create_superuser(
                    email=email, password=password, display_name="Administrator"
                )
                event = "administrator.created"
                action = "created"
            audit_event(event, actor=user, metadata={"method": "bootstrap_admin"})
        self.stdout.write(self.style.SUCCESS(f"Administrator {action} for {email}."))
