from django.contrib.auth.backends import ModelBackend

from .models import User


class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        email = (kwargs.get("email") or username or "").strip().lower()
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            User().set_password(password or "")
            return None
        if user.is_suspended or user.is_locked:
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        user.register_login_failure()
        return None

