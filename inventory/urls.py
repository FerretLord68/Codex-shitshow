from django.urls import path

from . import views

app_name = "inventory"
urlpatterns = [
    path("", views.inventory_list, name="list"),
    path("household/<uuid:household_id>/items/create/", views.item_create, name="item_create"),
    path("household/<uuid:household_id>/locations/create/", views.location_create, name="location_create"),
    path("household/<uuid:household_id>/waste/create/", views.waste_create, name="waste_create"),
    path("household/<uuid:household_id>/waste/", views.waste_report, name="waste_report"),
    path("meals/<uuid:meal_id>/prepare/", views.prepare_meal, name="prepare_meal"),
]

