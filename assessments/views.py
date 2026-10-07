import ast

from decimal import Decimal

from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Assessment, Document, Lender
from .serializers import AssessmentSerializer, DocumentSerializer, LenderSerializer
from .services import (
    DOCUMENT_LABELS,
    calculate_assessment,
    calculate_document_readiness_score,
    generate_lender_matches,
    get_required_documents,
)


class AssessmentViewSet(viewsets.ModelViewSet):
    queryset = Assessment.objects.all().order_by("-created_at")
    serializer_class = AssessmentSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assessment = serializer.save()
        return self._assessment_response(assessment, status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        assessment = self.get_object()
        return self._assessment_response(assessment)

    def update(self, request, *args, **kwargs):
        assessment = self.get_object()
        serializer = self.get_serializer(
            assessment,
            data=request.data,
            partial=request.method == "PATCH",
        )
        serializer.is_valid(raise_exception=True)
        assessment = serializer.save()
        return self._assessment_response(assessment)

    def _assessment_response(self, assessment, http_status=status.HTTP_200_OK):
        calculation = calculate_assessment(assessment)
        lender_records = Lender.objects.filter(
            loan_type__in=[assessment.route, "collateral", "non_collateral"]
        ).all()
        matches = generate_lender_matches(
            [
                {
                    "name": lender.name,
                    "loan_type": lender.loan_type,
                    "interest_rate": lender.interest_rate,
                    "minimum_cibil": lender.minimum_cibil,
                    "conditions": lender.conditions,
                    "document_categories": lender.document_categories,
                }
                for lender in lender_records
            ],
            assessment.cibil_score,
            assessment.route,
            assessment.collateral_value,
        )
        document_checklist = get_required_documents(
            assessment.route,
            assessment.co_applicant_type,
            assessment.property_state,
        )
        uploaded_document_types = list(
            assessment.documents.exclude(status="rejected")
            .values_list("document_type", flat=True)
            .distinct()
        )
        document_readiness = calculate_document_readiness_score(
            uploaded_document_types,
            document_checklist,
        )

        payload = {
            "assessment": AssessmentSerializer(assessment).data,
            "calculation": calculation,
            "lenders": matches,
            "document_checklist": list(document_checklist.values()),
            "document_readiness": document_readiness,
            "uploaded_document_types": uploaded_document_types,
        }
        return Response(payload, status=http_status)

    @action(detail=True, methods=["post"])
    def complete(self, request, *args, **kwargs):
        assessment = self.get_object()
        calculation = calculate_assessment(assessment)
        return Response(
            {
                "assessment": AssessmentSerializer(assessment).data,
                "calculation": calculation,
                "message": "Assessment generated. This is an estimate, not a loan guarantee.",
            }
        )


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all().order_by("-uploaded_at")
    serializer_class = DocumentSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        assessment_id = request.data.get("assessment")
        assessment = get_object_or_404(
            Assessment.objects.select_for_update(),
            pk=assessment_id,
        )
        file_obj = request.FILES.get("file")
        document_type = request.data.get("document_type")

        if isinstance(document_type, str):
            try:
                parsed_type = ast.literal_eval(document_type)
                if isinstance(parsed_type, list) and len(parsed_type) == 1:
                    document_type = parsed_type[0]
                elif isinstance(parsed_type, list):
                    return Response({"detail": "Unsupported document type."}, status=status.HTTP_400_BAD_REQUEST)
            except (ValueError, SyntaxError):
                pass

        allowed_types = {
            document_type: (".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png")
            for document_type in DOCUMENT_LABELS
        }
        allowed_types.update({
            "itr": (".pdf", ".doc", ".docx"),
            "bank_statement": (".pdf", ".csv"),
            "salary_slip": (".pdf", ".doc", ".docx"),
            "ca_net_worth": (".pdf", ".doc", ".docx"),
            "property_document": (".pdf", ".doc", ".docx"),
            "other": (".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png"),
        })
        if file_obj is None:
            return Response({"detail": "A file is required."}, status=status.HTTP_400_BAD_REQUEST)

        extension = file_obj.name.lower()[file_obj.name.lower().rfind(".") :]
        if extension.lower() not in allowed_types.get(document_type, ()):
            return Response({"detail": "Unsupported file type."}, status=status.HTTP_400_BAD_REQUEST)
        if file_obj.size > 10 * 1024 * 1024:
            return Response({"detail": "File size must be 10 MB or less."}, status=status.HTTP_400_BAD_REQUEST)

        serializer_data = request.data.copy()
        serializer_data["assessment"] = assessment.id
        serializer_data["document_type"] = document_type
        serializer = self.get_serializer(data=serializer_data)
        serializer.is_valid(raise_exception=True)
        document = serializer.save()
        response_data = DocumentSerializer(document).data
        required_documents = get_required_documents(
            assessment.route,
            assessment.co_applicant_type,
            assessment.property_state,
        )
        response_data["requires_self_attestation"] = True
        response_data["document_readiness"] = calculate_document_readiness_score(
            assessment.documents.exclude(status="rejected").values_list("document_type", flat=True),
            required_documents,
        )
        response_data["uploaded_document_types"] = list(
            assessment.documents.exclude(status="rejected")
            .values_list("document_type", flat=True)
            .distinct()
        )
        return Response(response_data, status=status.HTTP_201_CREATED)


class LenderViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Lender.objects.order_by("name", "loan_type")
    serializer_class = LenderSerializer

    @action(detail=False, methods=["get"])
    def available(self, request):
        loan_type = request.query_params.get("loan_type")
        queryset = self.get_queryset()
        if loan_type:
            queryset = queryset.filter(loan_type=loan_type)
        return Response(self.get_serializer(queryset, many=True).data)
