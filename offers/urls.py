from django.urls import path

from . import views

app_name = "offers"
urlpatterns = [
    path("", views.offer_list, name="list"),
    path("providers/", views.provider_admin, name="providers"),
    path("providers/<uuid:provider_id>/sync/", views.synchronize, name="synchronize"),
    path("import/", views.manual_import, name="manual_import"),
]

