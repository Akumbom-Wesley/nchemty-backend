"""
Re-exports all serializers so the rest of the codebase
imports from apps.kyc.serializers without knowing the
internal module structure.

Before modularization:
    from apps.kyc.serializers import StudentRegistrationSerializer

After modularization — same import, still works:
    from apps.kyc.serializers import StudentRegistrationSerializer
"""

from .student import StudentRegistrationSerializer, StudentReapplySerializer
from .personal import PersonalRegistrationSerializer, PersonalReapplySerializer
from .read import (
    StudentDocumentReadSerializer,
    StudentProfileReadSerializer,
    PersonalDocumentReadSerializer,
    PersonalProfileReadSerializer,
)

__all__ = [
    "StudentRegistrationSerializer",
    "StudentReapplySerializer",
    "PersonalRegistrationSerializer",
    "PersonalReapplySerializer",
    "StudentDocumentReadSerializer",
    "StudentProfileReadSerializer",
    "PersonalDocumentReadSerializer",
    "PersonalProfileReadSerializer",
]