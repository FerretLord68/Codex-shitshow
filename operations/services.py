import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import BackgroundJob

logger = logging.getLogger(__name__)


def enqueue(kind, payload, *, dedupe_key=None, run_after=None, max_attempts=5):
    if dedupe_key:
        existing = BackgroundJob.objects.filter(dedupe_key=dedupe_key).first()
        if existing:
            return existing
    return BackgroundJob.objects.create(
        kind=kind,
        payload=payload,
        dedupe_key=dedupe_key,
        run_after=run_after or timezone.now(),
        max_attempts=max_attempts,
    )


def claim_job():
    with transaction.atomic():
        job = (
            BackgroundJob.objects.select_for_update(skip_locked=True)
            .filter(status=BackgroundJob.Status.PENDING, run_after__lte=timezone.now())
            .order_by("run_after")
            .first()
        )
        if not job:
            return None
        job.status = BackgroundJob.Status.RUNNING
        job.locked_at = timezone.now()
        job.attempts += 1
        job.save(update_fields=["status", "locked_at", "attempts", "updated_at"])
        return job


def finish_job(job, error=None):
    if error is None:
        job.status = BackgroundJob.Status.SUCCEEDED
        job.completed_at = timezone.now()
        job.error_type = ""
        job.error_message = ""
    else:
        job.error_type = type(error).__name__
        job.error_message = str(error)[:500]
        if job.attempts >= job.max_attempts:
            job.status = BackgroundJob.Status.DEAD
        else:
            job.status = BackgroundJob.Status.PENDING
            job.run_after = timezone.now() + timedelta(seconds=min(3600, 2 ** job.attempts * 15))
        logger.exception("background_job_failed", extra={"event": "background_job_failed", "job_id": job.id})
    job.save()

