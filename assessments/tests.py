from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from rest_framework.test import APIClient

from assessments.models import Assessment, Lender
from assessments.services import (
    calculate_assessment,
    calculate_document_readiness_score,
    generate_lender_matches,
    get_required_documents,
)


@pytest.fixture
def api_client():
    return APIClient()


class TestDocumentReadinessEngine:
    def test_non_collateral_salaried_checklist_has_core_and_salaried_documents(self):
        documents = get_required_documents("non_collateral", "salaried", "Delhi")

        assert len(documents) == 13
        assert "pan_card" in documents
        assert "salary_slips_3m" in documents
        assert "title_deed" not in documents
        assert "delhi_conveyance_dda" not in documents
        assert all(document["requires_self_attestation"] for document in documents.values())

    def test_collateral_state_documents_are_profile_specific(self):
        delhi_documents = get_required_documents("collateral", "salaried", "Delhi")
        maharashtra_documents = get_required_documents("collateral", "self_employed", "Maharashtra")
        other_documents = get_required_documents("collateral", "self_employed", "Other")

        assert "delhi_conveyance_dda" in delhi_documents
        assert "mh_builder_noc_index2" not in delhi_documents
        assert "mh_builder_noc_index2" in maharashtra_documents
        assert "delhi_conveyance_dda" not in maharashtra_documents
        assert "title_deed" in other_documents
        assert "delhi_conveyance_dda" not in other_documents
        assert len(maharashtra_documents) == 20

    def test_rejects_unknown_profile_values(self):
        with pytest.raises(ValueError):
            get_required_documents("non_collateral", "contractor")
        with pytest.raises(ValueError):
            get_required_documents("collateral", "salaried", "Karnataka")

    def test_readiness_counts_unique_required_uploads_and_names_missing_documents(self):
        required = get_required_documents("non_collateral", "salaried")

        result = calculate_document_readiness_score(
            ["pan_card", "pan_card", "not_required"],
            required,
        )

        assert result["readiness_score"] == 7
        assert result["total_required"] == 13
        assert result["total_uploaded"] == 1
        assert result["missing_documents"][0] == {
            "key": "proof_of_residence",
            "label": "Proof of residence (Voter ID / Passport / Electricity Bill / Telephone Bill / Ration Card / Bank account statement / Government Identity Proof)",
            "requires_self_attestation": True,
        }
        assert result["is_ready_for_submission"] is False

    def test_all_required_uploads_produce_full_readiness(self):
        required = get_required_documents("non_collateral", "self_employed")

        result = calculate_document_readiness_score(list(required), required)

        assert result == {
            "readiness_score": 100,
            "total_required": 12,
            "total_uploaded": 12,
            "missing_documents": [],
            "is_ready_for_submission": True,
        }


@pytest.mark.django_db
class TestAssessmentCalculations:
    def test_calculates_total_study_cost_and_funding_gap(self):
        assessment = Assessment(
            tuition=20000,
            living_costs=8000,
            scholarships=3000,
            savings=5000,
            fees_paid=2000,
            family_contribution=5000,
            income=0,
            assets=0,
            liabilities=0,
            collateral_value=0,
        )

        result = calculate_assessment(assessment)

        assert result["total_study_cost"] == Decimal("28000")
        assert result["funding_gap"] == Decimal("13000")
        assert result["net_worth"] == Decimal("0")

    def test_calculates_net_worth_and_missing_data_warning(self):
        assessment = Assessment(
            tuition=20000,
            living_costs=8000,
            scholarships=0,
            savings=0,
            fees_paid=0,
            family_contribution=0,
            income=50000,
            assets=100000,
            liabilities=40000,
            collateral_value=0,
        )

        result = calculate_assessment(assessment)

        assert result["net_worth"] == Decimal("110000")
        assert any("Missing required financial information" in warning for warning in result["warnings"])

    def test_rejects_negative_money_values(self):
        assessment = Assessment(
            tuition=-1,
            living_costs=0,
            scholarships=0,
            savings=0,
            fees_paid=0,
            family_contribution=0,
            income=0,
            assets=0,
            liabilities=0,
            collateral_value=0,
        )

        with pytest.raises(ValidationError):
            assessment.clean()


@pytest.mark.django_db
class TestLenderMatching:
    def test_matches_collateral_lenders_by_cibil_and_route(self):
        lenders = [
            {
                "name": "SBI",
                "loan_type": "collateral",
                "interest_rate": Decimal("8.40"),
                "minimum_cibil": 750,
                "document_categories": ["academic", "basic", "property"],
            },
            {
                "name": "BOI",
                "loan_type": "collateral",
                "interest_rate": Decimal("9.00"),
                "minimum_cibil": 670,
                "document_categories": ["academic", "basic", "property"],
            },
        ]

        matches = generate_lender_matches(lenders, 800, "collateral", 150000)

        assert [lender["name"] for lender in matches] == ["SBI", "BOI"]

    def test_keeps_only_lenders_that_are_possible_for_the_given_route(self):
        lenders = [
            {"name": "BOI", "loan_type": "non_collateral", "interest_rate": Decimal("9.00"), "minimum_cibil": 670},
            {"name": "SBI", "loan_type": "collateral", "interest_rate": Decimal("8.40"), "minimum_cibil": 750},
        ]

        matches = generate_lender_matches(lenders, 800, "non_collateral", 0)

        assert [lender["name"] for lender in matches] == ["BOI"]


@pytest.mark.django_db
class TestAssessmentApi:
    def test_creates_assessment_and_returns_calculation(self, api_client):
        response = api_client.post(
            "/api/assessments/",
            {
                "country": "United States",
                "university": "Example University",
                "course": "Computer Science",
                "tuition": "20000",
                "living_costs": "8000",
                "scholarships": "3000",
                "savings": "5000",
                "fees_paid": "2000",
                "family_contribution": "5000",
                "income": "0",
                "assets": "0",
                "liabilities": "0",
                "collateral_value": "0",
                "cibil_score": "750",
                "route": "non_collateral",
            },
            format="json",
        )

        assert response.status_code == 201
        assert response.data["calculation"]["funding_gap"] == Decimal("13000.00")
        assert response.data["assessment"]["country"] == "United States"
        assert len(response.data["document_checklist"]) == 13
        assert response.data["document_readiness"]["readiness_score"] == 0

    def test_assessment_api_uses_profile_to_build_collateral_state_checklist(self, api_client):
        response = api_client.post(
            "/api/assessments/",
            {
                "route": "collateral",
                "collateral_value": "100000",
                "cibil_score": "750",
                "co_applicant_type": "self_employed",
                "property_state": "Maharashtra",
            },
            format="json",
        )

        assert response.status_code == 201
        document_keys = {document["key"] for document in response.data["document_checklist"]}
        assert len(document_keys) == 20
        assert "mh_builder_noc_index2" in document_keys
        assert "delhi_conveyance_dda" not in document_keys
        assert all(
            document["requires_self_attestation"]
            for document in response.data["document_checklist"]
        )

    def test_document_upload_returns_updated_readiness_score(self, api_client):
        assessment = Assessment.objects.create(
            country="United States",
            route="non_collateral",
            co_applicant_type="salaried",
        )
        file_obj = SimpleUploadedFile("pan-card.pdf", b"%PDF-1.4\n%%EOF", content_type="application/pdf")

        response = api_client.post(
            "/api/documents/",
            {
                "assessment": assessment.id,
                "document_type": "pan_card",
                "file": file_obj,
            },
        )

        assert response.status_code == 201
        assert response.data["requires_self_attestation"] is True
        assert response.data["document_readiness"]["total_uploaded"] == 1
        assert response.data["document_readiness"]["total_required"] == 13
        assert response.data["document_readiness"]["readiness_score"] == 7

    def test_rejects_duplicate_active_document_type_for_assessment(self, api_client):
        assessment = Assessment.objects.create(country="United States")
        upload_data = {
            "assessment": assessment.id,
            "document_type": "pan_card",
            "file": SimpleUploadedFile(
                "pan-card.pdf", b"%PDF-1.4\n%%EOF", content_type="application/pdf"
            ),
        }

        first_response = api_client.post("/api/documents/", upload_data.copy())
        duplicate_response = api_client.post(
            "/api/documents/",
            {
                **upload_data,
                "file": SimpleUploadedFile(
                    "another-pan-card.pdf", b"%PDF-1.4\n%%EOF", content_type="application/pdf"
                ),
            },
        )

        assert first_response.status_code == 201
        assert duplicate_response.status_code == 400
        assert "already been uploaded" in str(duplicate_response.data["document_type"])
        assert assessment.documents.count() == 1

    def test_rejects_unsupported_document_type(self, api_client):
        assessment = Assessment.objects.create(
            country="United States",
            tuition=20000,
            living_costs=8000,
            scholarships=3000,
            savings=5000,
            fees_paid=2000,
            family_contribution=5000,
            income=0,
            assets=0,
            liabilities=0,
            collateral_value=0,
        )
        file_obj = SimpleUploadedFile("notes.txt", b"not a valid document", content_type="text/plain")

        response = api_client.post(
            "/api/documents/",
            {
                "assessment": assessment.id,
                "document_type": "itr",
                "file": file_obj,
            },
        )

        assert response.status_code == 400
        assert response.data["detail"] == "Unsupported file type."

    def test_accepts_legacy_array_string_document_type(self, api_client):
        assessment = Assessment.objects.create(
            country="United States",
            tuition=20000,
            living_costs=8000,
            scholarships=3000,
            savings=5000,
            fees_paid=2000,
            family_contribution=5000,
            income=0,
            assets=0,
            liabilities=0,
            collateral_value=0,
        )
        file_obj = SimpleUploadedFile(
            "bank-statement.pdf",
            b"%PDF-1.4\n%%EOF",
            content_type="application/pdf",
        )

        response = api_client.post(
            "/api/documents/",
            {
                "assessment": assessment.id,
                "document_type": "['bank_statement']",
                "file": file_obj,
            },
            format="multipart",
        )

        assert response.status_code == 201
        assert response.data["document_type"] == "bank_statement"


@pytest.mark.django_db
class TestLenderSeedCommand:
    def test_loads_non_decimal_interest_rate_values_without_crashing(self):
        Lender.objects.all().delete()

        call_command("seed_lenders")

        assert Lender.objects.count() == 10
        assert Lender.objects.get(name="BOI", loan_type="non_collateral").interest_rate == "Not possible"
        assert Lender.objects.get(name="Credila", loan_type="collateral").interest_rate == "9.25 - 9.75"
