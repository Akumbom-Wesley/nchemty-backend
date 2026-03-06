from django.urls import path

from .views import ChangePasswordView, MeView, RoleListView

app_name = "users"

urlpatterns = [
    path("roles/", RoleListView.as_view(), name="role-list"),
    path("me/", MeView.as_view(), name="me"),
    path("me/change-password/", ChangePasswordView.as_view(), name="change-password"),
]