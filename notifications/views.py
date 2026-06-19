from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def notification_list(request):
    return render(request, "notifications/list.html", {"notifications": request.user.notifications.all()[:200]})


@login_required
@require_POST
def mark_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.read_at = timezone.now()
    notification.save(update_fields=["read_at"])
    return redirect(notification.action_url or "notifications:list")

