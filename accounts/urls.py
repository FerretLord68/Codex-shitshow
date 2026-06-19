from django.urls import path

from . import views

app_name = "accounts"
urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("verify/<str:token>/", views.verify_email, name="verify"),
    path("password-reset/", views.password_reset_request, name="password_reset_request"),
    path("reset/<str:token>/", views.password_reset_confirm, name="password_reset_confirm"),
    path("settings/", views.settings_view, name="settings"),
    path("password/", views.password_change, name="password_change"),
    path("sessions/", views.sessions, name="sessions"),
    path("sessions/<uuid:session_id>/revoke/", views.revoke_session, name="revoke_session"),
    path("export/", views.export_data, name="export"),
    path("delete/", views.delete_account, name="delete"),
]

