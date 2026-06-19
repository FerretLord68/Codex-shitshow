from django.urls import path

from . import views

app_name = "shopping"
urlpatterns = [
    path("", views.shopping_list_index, name="list"),
    path("household/<uuid:household_id>/create/", views.create, name="create"),
    path("<uuid:list_id>/", views.detail, name="detail"),
    path("items/<uuid:item_id>/toggle/", views.toggle_item, name="toggle_item"),
    path("items/<uuid:item_id>/purchase/", views.purchase_item, name="purchase_item"),
]

