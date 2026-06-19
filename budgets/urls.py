from django.urls import path

from . import views

app_name = "budgets"
urlpatterns = [
    path("<uuid:household_id>/", views.overview, name="overview"),
    path("<uuid:household_id>/create/", views.create, name="create"),
]

