from django.urls import path

from . import views

app_name = "planning"
urlpatterns = [
    path("", views.plan_list, name="list"),
    path("household/<uuid:household_id>/create/", views.create, name="create"),
    path("<uuid:plan_id>/", views.detail, name="detail"),
    path("<uuid:plan_id>/meals/create/", views.meal_create, name="meal_create"),
    path("<uuid:plan_id>/generate/", views.generate, name="generate"),
    path("<uuid:plan_id>/nutrition/", views.nutrition, name="nutrition"),
    path("meals/<uuid:meal_id>/edit/", views.meal_edit, name="meal_edit"),
    path("meals/<uuid:meal_id>/status/", views.meal_status, name="meal_status"),
]

