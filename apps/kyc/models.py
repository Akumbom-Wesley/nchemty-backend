import os
import uuid

from django.conf import settings
from django.db import models

from .validators import validate_document_file, validate_passport_photo


def kyc_document_upload_path(instance, filename):
    """
    Builds a non-guessable upload path per user per document type.

    Structure:
      kyc/<user_id>/<document_type>/<uuid>.<ext>

    UUID in the filename means even if two users upload a file
    with the same name, paths never collide or overwrite each other.
    """
    ext = os.path.splitext(filename)[1].lower()
    unique_name = f"{uuid.uuid4()}{ext}"
    return f"kyc/{instance.profile.user_id}/{instance.document_type}/{unique_name}"


# ── Student Profile ───────────────────────────────────────────────────────────

class StudentProfile(models.Model):
    """
    KYC profile for users with role='student'.

    Stores student-specific identity data alongside links to
    their uploaded KYC documents. Kept separate from User so
    the User model stays lean and role-agnostic.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile",
    )

    # Admin review metadata
    admin_notes = models.TextField(
        blank=True,
        help_text="Internal reviewer notes. Never shown to the applicant.",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_student_profiles",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Student Profile"
        verbose_name_plural = "Student Profiles"

    def __str__(self):
        return f"Student Profile — {self.user.get_full_name()} ({self.user.email})"

    def has_all_required_documents(self):
        """
        Checks that all three required document types have been uploaded.
        Used by admin review and serializer pre-submit validation.
        """
        required = {
            StudentDocument.DocumentType.NATIONAL_ID,
            StudentDocument.DocumentType.LOCATION_PLAN,
            StudentDocument.DocumentType.PASSPORT_PHOTO,
        }
        submitted = set(
            self.documents.values_list("document_type", flat=True)
        )
        return required.issubset(submitted)


class StudentDocument(models.Model):
    """
    One uploaded KYC document for a student.
    Each document type can only be submitted once per profile —
    enforced by unique_together at the DB level.
    """

    class DocumentType(models.TextChoices):
        NATIONAL_ID = "national_id", "National ID Card (CNI)"
        LOCATION_PLAN = "location_plan", "Location Plan"
        PASSPORT_PHOTO = "passport_photo", "Passport Photo"

    profile = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(
        max_length=50,
        choices=DocumentType.choices,
    )
    file = models.FileField(
        upload_to=kyc_document_upload_path,
    )
    original_filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Student Document"
        verbose_name_plural = "Student Documents"
        unique_together = [("profile", "document_type")]

    def __str__(self):
        return f"{self.get_document_type_display()} — {self.profile.user.get_full_name()}"


# ── Personal Profile ──────────────────────────────────────────────────────────

class PersonalProfile(models.Model):
    """
    KYC profile for users with role='personal'.

    NIU (Numéro d'Identifiant Unique) is optional — not all
    individuals have one depending on their tax registration status.
    Location plan is required.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="personal_profile",
    )

    # NIU — optional tax identifier
    niu = models.CharField(
        max_length=50,
        blank=True,
        help_text="Numéro d'Identifiant Unique (optional).",
    )

    # Admin review metadata
    admin_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_personal_profiles",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Personal Profile"
        verbose_name_plural = "Personal Profiles"

    def __str__(self):
        return f"Personal Profile — {self.user.get_full_name()} ({self.user.email})"

    def has_all_required_documents(self):
        """
        Personal accounts only require the location plan.
        NIU document is optional.
        """
        required = {PersonalDocument.DocumentType.LOCATION_PLAN}
        submitted = set(
            self.documents.values_list("document_type", flat=True)
        )
        return required.issubset(submitted)


class PersonalDocument(models.Model):
    """
    One uploaded KYC document for a personal account.
    """

    class DocumentType(models.TextChoices):
        LOCATION_PLAN = "location_plan", "Location Plan"
        NIU_DOCUMENT = "niu_document", "NIU Document (optional)"

    profile = models.ForeignKey(
        PersonalProfile,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(
        max_length=50,
        choices=DocumentType.choices,
    )
    file = models.FileField(
        upload_to=kyc_document_upload_path,
    )
    original_filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Personal Document"
        verbose_name_plural = "Personal Documents"
        unique_together = [("profile", "document_type")]

    def __str__(self):
        return f"{self.get_document_type_display()} — {self.profile.user.get_full_name()}"