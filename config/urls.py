from django.contrib import admin
from django.urls import include, path

from common.views import dashboard, landing, legal_page, set_language

urlpatterns = [
    path("", landing, name="landing"),
    path("dashboard/", dashboard, name="dashboard"),
    path("language/<str:language>/", set_language, name="set_language"),
    path("privacy/", legal_page, {"page": "privacy"}, name="privacy"),
    path("terms/", legal_page, {"page": "terms"}, name="terms"),
    path("cookies/", legal_page, {"page": "cookies"}, name="cookies"),
    path("account/", include("accounts.urls")),
    path("households/", include("households.urls")),
    path("recipes/", include("recipes.urls")),
    path("planning/", include("planning.urls")),
    path("inventory/", include("inventory.urls")),
    path("shopping/", include("shopping.urls")),
    path("offers/", include("offers.urls")),
    path("budgets/", include("budgets.urls")),
    path("notifications/", include("notifications.urls")),
    path("ops/", include("operations.urls")),
    path("admin/", admin.site.urls),
]
