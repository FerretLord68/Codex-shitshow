from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import check_for_language


def landing(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse("dashboard"))
    return render(request, "landing.html")


@login_required
def dashboard(request):
    memberships = request.user.memberships.filter(is_active=True).select_related("household")
    household = memberships.first().household if memberships else None
    context = {"memberships": memberships, "household": household}
    if household:
        from inventory.models import InventoryItem
        from notifications.models import Notification
        from planning.models import PlannedMeal
        from shopping.models import ShoppingList

        context.update({
            "today_meals": PlannedMeal.objects.filter(
                household=household, date=__import__("datetime").date.today()
            ).select_related("recipe"),
            "expiring": InventoryItem.objects.expiring_soon().filter(household=household)[:6],
            "shopping_lists": ShoppingList.objects.filter(
                household=household, status__in=["draft", "active", "shopping"]
            )[:4],
            "notifications": Notification.objects.filter(user=request.user, read_at__isnull=True)[:5],
        })
    return render(request, "dashboard.html", context)


def set_language(request, language):
    if not check_for_language(language):
        language = "da"
    response = HttpResponseRedirect(request.META.get("HTTP_REFERER", reverse("landing")))
    response.set_cookie("django_language", language, max_age=31536000, samesite="Lax", secure=True)
    return response


def legal_page(request, page):
    if page not in {"privacy", "terms", "cookies"}:
        from django.http import Http404
        raise Http404
    return render(request, f"legal/{page}.html")
