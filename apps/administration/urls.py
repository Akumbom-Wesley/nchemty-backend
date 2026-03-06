from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    PersonalProfileViewSet,
    StudentProfileViewSet,
    UserManagementViewSet,
)

router = DefaultRouter()
router.register(r"students", StudentProfileViewSet, basename="admin-students")
router.register(r"personal", PersonalProfileViewSet, basename="admin-personal")
router.register(r"users", UserManagementViewSet, basename="admin-users")

app_name = "administration"

urlpatterns = [
    path("", include(router.urls)),
]