import getpass
from pathlib import Path

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
        parser.add_argument("--password-file")
        parser.add_argument("--yes-upgrade", action="store_true")
        parser.add_argument("--non-interactive", action="store_true")

    def handle(self, *args, **options):
        if User.objects.filter(is_superuser=True).exists():
            raise CommandError("Administrator bootstrap is already complete.")
        default_email = options["email"]
        entered = (
            ""
            if options["non_interactive"]
            else input(f"Administrator e-mail [{default_email}]: ").strip()
        )
        email = User.objects.normalize_email(entered or default_email).strip().lower()
        existing = User.objects.filter(email=email).first()
        candidate = existing or User(email=email, username=email, display_name="Administrator")
        if not existing:
            try:
                candidate.full_clean(exclude=["password"])
            except ValidationError as error:
                raise CommandError(" ".join(error.messages)) from error
        if existing:
            approved = options["yes_upgrade"]
            if not approved and not options["non_interactive"]:
                answer = input(
                    "A normal user exists for this address. Upgrade it to administrator? [y/N]: "
                )
                approved = answer.strip().lower() in {"y", "yes"}
            if not approved:
                raise CommandError("Administrator bootstrap cancelled.")
        if options["password_file"]:
            password_path = Path(options["password_file"])
            try:
                mode = password_path.stat().st_mode & 0o777
                if mode & 0o077:
                    raise CommandError("Password file must not be accessible by group or others.")
                password = password_path.read_text().rstrip("\r\n")
            except OSError as error:
                raise CommandError("Unable to read password file.") from error
            confirmation = password
        elif options["non_interactive"]:
            raise CommandError("--non-interactive requires --password-file.")
        else:
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
