from django.urls import path

from . import views

app_name = "recipes"
urlpatterns = [
    path("", views.recipe_list, name="list"),
    path("household/<uuid:household_id>/create/", views.create, name="create"),
    path("household/<uuid:household_id>/import/", views.import_recipe, name="import"),
    path("<uuid:recipe_id>/", views.detail, name="detail"),
    path("<uuid:recipe_id>/edit/", views.edit, name="edit"),
    path("<uuid:recipe_id>/duplicate/", views.duplicate, name="duplicate"),
    path("<uuid:recipe_id>/export/", views.export_recipe, name="export"),
    path("<uuid:recipe_id>/images/upload/", views.upload_image, name="upload_image"),
    path("images/<uuid:image_id>/", views.serve_image, name="serve_image"),
]
