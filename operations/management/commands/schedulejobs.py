from django.core.management.base import BaseCommand

from operations.services import enqueue


class Command(BaseCommand):
    help = "Enqueue periodic idempotent maintenance jobs."

    def handle(self, *args, **options):
        from django.utils import timezone

        day = timezone.localdate().isoformat()
        enqueue("notifications.expiration", {}, dedupe_key=f"expiration:{day}")
        self.stdout.write(self.style.SUCCESS("Scheduled periodic jobs"))

