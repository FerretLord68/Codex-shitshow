from django.urls import path

from . import views

app_name = "households"
urlpatterns = [
    path("", views.household_list, name="list"),
    path("create/", views.create, name="create"),
    path("invitations/<str:token>/", views.accept_invitation, name="accept_invitation"),
    path("<uuid:household_id>/", views.detail, name="detail"),
    path("<uuid:household_id>/edit/", views.edit, name="edit"),
    path("<uuid:household_id>/invite/", views.invite, name="invite"),
    path("<uuid:household_id>/invitations/<uuid:invitation_id>/revoke/", views.revoke_invitation, name="revoke_invitation"),
    path("<uuid:household_id>/profiles/create/", views.profile_create, name="profile_create"),
    path("<uuid:household_id>/ownership/<uuid:membership_id>/", views.transfer_ownership, name="transfer_ownership"),
]

