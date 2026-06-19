from django.contrib.admin.views.decorators import staff_member_required
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from .models import BackgroundJob, ServiceHeartbeat


def health(request):
    return JsonResponse({"status": "ok"})


def openapi(request):
    return JsonResponse({
        "openapi": "3.1.0",
        "info": {"title": "MealHouse internal API", "version": "1.0.0"},
        "servers": [{"url": "/"}],
        "paths": {
            "/ops/health/": {
                "get": {
                    "summary": "Non-sensitive liveness",
                    "responses": {"200": {"description": "Application process is alive"}},
                }
            },
            "/shopping/items/{item_id}/toggle/": {
                "post": {
                    "summary": "Update a shopping item with optimistic concurrency",
                    "parameters": [{"name": "item_id", "in": "path", "required": True, "schema": {"type": "string", "format": "uuid"}}],
                    "responses": {
                        "200": {"description": "Updated"},
                        "403": {"description": "Not authorized"},
                        "409": {"description": "Version conflict"},
                    },
                }
            },
        },
    })


def readiness(request):
    if request.META.get("REMOTE_ADDR") not in {"127.0.0.1", "::1"}:
        return JsonResponse({"status": "not_found"}, status=404)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        worker = ServiceHeartbeat.objects.filter(service="worker").first()
        ready = bool(worker and (timezone.now() - worker.last_seen_at).total_seconds() < 120)
        return JsonResponse({"status": "ready" if ready else "degraded", "database": "ok", "worker": ready}, status=200 if ready else 503)
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)


@staff_member_required
def jobs(request):
    return render(request, "operations/jobs.html", {"jobs": BackgroundJob.objects.order_by("-created_at")[:200]})
