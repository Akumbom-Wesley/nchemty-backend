from django.urls import path

from .views import (
    PersonalReapplyView,
    PersonalRegisterView,
    StudentReapplyView,
    StudentRegisterView,
)

app_name = "kyc"

urlpatterns = [
    # ── Registration ──────────────────────────────────────────────────
    path("register/student/", StudentRegisterView.as_view(), name="register-student"),
    path("register/personal/", PersonalRegisterView.as_view(), name="register-personal"),

    # ── Reapplication ─────────────────────────────────────────────────
    path("reapply/student/", StudentReapplyView.as_view(), name="reapply-student"),
    path("reapply/personal/", PersonalReapplyView.as_view(), name="reapply-personal"),
]