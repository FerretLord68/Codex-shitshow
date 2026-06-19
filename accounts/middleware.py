from datetime import timedelta

from django.conf import settings
from django.contrib.auth import logout
from django.utils import timezone

from .models import UserSession


class ActiveSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.session.session_key:
            digest = UserSession.hash_key(request.session.session_key)
            tracked = UserSession.objects.filter(user=request.user, session_key_hash=digest).first()
            if tracked and not tracked.active:
                logout(request)
            elif tracked:
                if tracked.last_seen_at < timezone.now() - timedelta(minutes=5):
                    tracked.last_seen_at = timezone.now()
                    tracked.save(update_fields=["last_seen_at"])
            else:
                UserSession.objects.create(
                    user=request.user,
                    session_key_hash=digest,
                    user_agent=request.META.get("HTTP_USER_AGENT", "")[:300],
                    ip_address=getattr(request, "client_ip", None) or None,
                    expires_at=timezone.now() + timedelta(seconds=settings.SESSION_COOKIE_AGE),
                )
        return self.get_response(request)

