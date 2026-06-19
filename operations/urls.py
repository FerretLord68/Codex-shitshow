from django.urls import path

from . import views

app_name = "operations"
urlpatterns = [
    path("health/", views.health, name="health"),
    path("openapi.json", views.openapi, name="openapi"),
    path("readiness/", views.readiness, name="readiness"),
    path("jobs/", views.jobs, name="jobs"),
]
