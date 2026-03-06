from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.throttles import RegistrationRateThrottle
from .serializers import (
    PersonalReapplySerializer,
    PersonalRegistrationSerializer,
    StudentReapplySerializer,
    StudentRegistrationSerializer,
)


class StudentRegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [RegistrationRateThrottle]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = StudentRegistrationSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                "detail": (
                    "Your student account application has been submitted. "
                    "Our team will review your documents and notify you by email."
                )
            },
            status=status.HTTP_201_CREATED,
        )


class PersonalRegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [RegistrationRateThrottle]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = PersonalRegistrationSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                "detail": (
                    "Your personal account application has been submitted. "
                    "Our team will review your documents and notify you by email."
                )
            },
            status=status.HTTP_201_CREATED,
        )


class StudentReapplyView(APIView):
    """
    POST /api/v1/auth/reapply/student/

    For rejected student accounts to reapply with new documents.
    Requires email + password to authenticate before accepting documents.
    """

    permission_classes = [AllowAny]
    throttle_classes = [RegistrationRateThrottle]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = StudentReapplySerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                "detail": (
                    "Your reapplication has been submitted. "
                    "Our team will review your new documents and notify you by email."
                )
            },
            status=status.HTTP_200_OK,
        )


class PersonalReapplyView(APIView):
    """
    POST /api/v1/auth/reapply/personal/

    For rejected personal accounts to reapply with new documents.
    """

    permission_classes = [AllowAny]
    throttle_classes = [RegistrationRateThrottle]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = PersonalReapplySerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                "detail": (
                    "Your reapplication has been submitted. "
                    "Our team will review your new documents and notify you by email."
                )
            },
            status=status.HTTP_200_OK,
        )