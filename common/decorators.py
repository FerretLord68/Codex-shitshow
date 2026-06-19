from functools import wraps

from django.core.exceptions import PermissionDenied

from households.models import Membership


def household_permission(permission):
    def decorator(view):
        @wraps(view)
        def wrapper(request, household_id, *args, **kwargs):
            membership = Membership.objects.filter(
                household_id=household_id,
                user=request.user,
                is_active=True,
            ).first()
            if not membership or not membership.has_permission(permission):
                raise PermissionDenied
            request.membership = membership
            request.household = membership.household
            return view(request, household_id, *args, **kwargs)

        return wrapper

    return decorator

