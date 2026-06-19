import signal
import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from operations.models import ServiceHeartbeat
from operations.services import claim_job, finish_job


class Command(BaseCommand):
    help = "Run the database-backed MealHouse background worker."

    def handle(self, *args, **options):
        stopping = False

        def stop(*_):
            nonlocal stopping
            stopping = True

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        while not stopping:
            ServiceHeartbeat.objects.update_or_create(
                service="worker", defaults={"last_seen_at": timezone.now()}
            )
            job = claim_job()
            if not job:
                time.sleep(2)
                continue
            try:
                self.dispatch(job)
            except Exception as error:
                finish_job(job, error)
            else:
                finish_job(job)

    def dispatch(self, job):
        if job.kind == "email.send":
            from notifications.services import deliver_email

            deliver_email(job.payload)
        elif job.kind == "offers.sync":
            from offers.services import synchronize_provider

            synchronize_provider(**job.payload)
        elif job.kind == "notifications.expiration":
            from notifications.services import create_expiration_notifications

            create_expiration_notifications(**job.payload)
        elif job.kind == "account.export":
            return
        else:
            raise ValueError(f"Unknown job kind: {job.kind}")

