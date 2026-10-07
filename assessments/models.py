from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .services import DOCUMENT_LABELS


class Assessment(models.Model):
    ROUTE_CHOICES = [
        ("collateral", "Collateral"),
        ("non_collateral", "Non-collateral"),
    ]
    CO_APPLICANT_TYPE_CHOICES = [
        ("salaried", "Salaried"),
        ("self_employed", "Self-employed"),
    ]
    PROPERTY_STATE_CHOICES = [
        ("Delhi", "Delhi"),
        ("Maharashtra", "Maharashtra"),
        ("Other", "Other"),
    ]

    country = models.CharField(max_length=100, blank=True)
    university = models.CharField(max_length=255, blank=True)
    course = models.CharField(max_length=255, blank=True)

    tuition = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    living_costs = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    scholarships = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    savings = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    fees_paid = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    family_contribution = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    income = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    assets = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    liabilities = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    collateral_value = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    cibil_score = models.PositiveIntegerField(default=0)
    route = models.CharField(max_length=20, choices=ROUTE_CHOICES, default="non_collateral")
    co_applicant_type = models.CharField(
        max_length=20, choices=CO_APPLICANT_TYPE_CHOICES, default="salaried"
    )
    property_state = models.CharField(
        max_length=20, choices=PROPERTY_STATE_CHOICES, default="Other"
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        errors = {}
        for field_name in (
            "tuition",
            "living_costs",
            "scholarships",
            "savings",
            "fees_paid",
            "family_contribution",
            "income",
            "assets",
            "liabilities",
            "collateral_value",
        ):
            value = getattr(self, field_name)
            if value < Decimal("0"):
                errors[field_name] = "Money values cannot be negative."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Assessment #{self.pk or 'new'}"


class Document(models.Model):
    DOCUMENT_TYPE_CHOICES = [
        *DOCUMENT_LABELS.items(),
        ("itr", "ITR"),
        ("bank_statement", "Bank statement"),
        ("salary_slip", "Salary slip"),
        ("ca_net_worth", "CA net worth certificate"),
        ("property_document", "Property document"),
        ("other", "Other"),
    ]
    STATUS_CHOICES = [
        ("uploaded", "Uploaded"),
        ("verified", "Verified"),
        ("rejected", "Rejected"),
    ]

    assessment = models.ForeignKey(Assessment, related_name="documents", on_delete=models.CASCADE)
    document_type = models.CharField(max_length=40, choices=DOCUMENT_TYPE_CHOICES)
    file = models.FileField(upload_to="documents/%Y/%m/%d/")
    uploaded_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="uploaded")

    def __str__(self) -> str:
        return f"{self.get_document_type_display()} for assessment {self.assessment_id}"


class Lender(models.Model):
    name = models.CharField(max_length=100)
    loan_type = models.CharField(max_length=30)
    interest_rate = models.CharField(max_length=50)
    minimum_cibil = models.PositiveIntegerField(null=True, blank=True)
    conditions = models.TextField(blank=True)
    document_categories = models.JSONField(default=list)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["name", "loan_type"], name="unique_lender_loan_type"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.loan_type})"
