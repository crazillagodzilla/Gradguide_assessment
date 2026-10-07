from rest_framework import serializers

from .models import Assessment, Document, Lender


class AssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assessment
        fields = [
            "id",
            "country",
            "university",
            "course",
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
            "cibil_score",
            "route",
            "co_applicant_type",
            "property_state",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class DocumentSerializer(serializers.ModelSerializer):
    requires_self_attestation = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "assessment",
            "document_type",
            "file",
            "uploaded_at",
            "status",
            "requires_self_attestation",
        ]
        read_only_fields = ["id", "uploaded_at", "status"]

    def get_requires_self_attestation(self, document):
        return True

    def validate(self, attrs):
        assessment = attrs.get("assessment", getattr(self.instance, "assessment", None))
        document_type = attrs.get("document_type", getattr(self.instance, "document_type", None))
        existing_documents = Document.objects.filter(
            assessment=assessment,
            document_type=document_type,
        ).exclude(status="rejected")
        if self.instance:
            existing_documents = existing_documents.exclude(pk=self.instance.pk)
        if existing_documents.exists():
            raise serializers.ValidationError({
                "document_type": "This document type has already been uploaded for this assessment."
            })
        return attrs


class LenderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lender
        fields = [
            "id",
            "name",
            "loan_type",
            "interest_rate",
            "minimum_cibil",
            "conditions",
            "document_categories",
        ]
