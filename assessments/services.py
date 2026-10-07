from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError


DOCUMENT_CATEGORIES = {
    "basic_documents": {
        "pan_card": "PAN Card",
        "proof_of_residence": "Proof of residence (Voter ID / Passport / Electricity Bill / Telephone Bill / Ration Card / Bank account statement / Government Identity Proof)",
        "bank_statement_6m": "Bank account statement for last 6 months (personal / salary)",
        "asset_liability_statement": "Personal Asset & Liability Statement",
    },
    "academic_documents": {
        "marksheets": "10th, 12th, and Degree marksheets/certificates",
        "admission_proof": "Proof of admission showing total course duration",
        "fee_structure": "Fee structure (I-20 for US, if available)",
        "test_scores": "IELTS / GMAT / GRE score card",
        "university_ranking": "University ranking print-out",
    },
    "co_applicant_salaried": {
        "salary_slips_3m": "Latest salary slips (last 3 months)",
        "form_16_2y": "Form 16 (last 2 years)",
        "employer_id": "Employer ID card",
        "itr_2y": "ITR (last 2 years)",
    },
    "co_applicant_self_employed": {
        "itr_3y": "ITR (last 3 years)",
        "financial_statements_3y": "Balance sheet and Profit & Loss account (last 3 years)",
        "business_address_proof": "Proof of business address",
    },
    "collateral_property_documents": {
        "title_deed": "Property title deed and registered sale agreement",
        "registration_receipt": "Original registration receipt",
        "municipal_allotment": "Allotment letter by Municipal Corporation / authorised government authority",
        "encumbrance_cert_30y": "Previous chain of sale deeds / Encumbrance Certificate (EC) of last 30 years",
        "property_tax_receipt": "Latest property tax bill or electricity bill with same address",
        "approved_building_plan": "Municipality-approved building plan or plot layout",
        "occupancy_certificate": "Occupancy Certificate (OC) (if apartment)",
    },
    "state_specific_collateral": {
        "Delhi": {
            "delhi_conveyance_dda": "Conveyance deed and DDA allotment letter",
        },
        "Maharashtra": {
            "mh_builder_noc_index2": "NOC from builder/society with Index II, share certificate, society conveyance deed, POA confirmation, commencement certificate, and board resolution",
        },
    },
}
DOCUMENT_LABELS = {
    key: label
    for category_name, documents in DOCUMENT_CATEGORIES.items()
    if category_name != "state_specific_collateral"
    for key, label in documents.items()
}
for state_documents in DOCUMENT_CATEGORIES["state_specific_collateral"].values():
    DOCUMENT_LABELS.update(state_documents)


def get_required_documents(
    route: str,
    co_applicant_type: str,
    property_state: str | None = None,
) -> dict[str, dict[str, str | bool]]:
    """Return the document checklist for a loan route and applicant profile."""
    if route not in {"collateral", "non_collateral"}:
        raise ValueError("route must be 'collateral' or 'non_collateral'.")
    if co_applicant_type not in {"salaried", "self_employed"}:
        raise ValueError("co_applicant_type must be 'salaried' or 'self_employed'.")
    if property_state not in {None, "Delhi", "Maharashtra", "Other"}:
        raise ValueError("property_state must be 'Delhi', 'Maharashtra', or 'Other'.")

    categories = [
        ("basic_documents", DOCUMENT_CATEGORIES["basic_documents"]),
        ("academic_documents", DOCUMENT_CATEGORIES["academic_documents"]),
        (
            f"co_applicant_{co_applicant_type}",
            DOCUMENT_CATEGORIES[f"co_applicant_{co_applicant_type}"],
        ),
    ]
    if route == "collateral":
        categories.append((
            "collateral_property_documents",
            DOCUMENT_CATEGORIES["collateral_property_documents"],
        ))
        state_documents = DOCUMENT_CATEGORIES["state_specific_collateral"].get(property_state, {})
        if state_documents:
            categories.append(("state_specific_collateral", state_documents))

    required_documents = {}
    for category_name, category in categories:
        for key, label in category.items():
            required_documents[key] = {
                "key": key,
                "label": label,
                "category": category_name,
                "requires_self_attestation": True,
            }
    return required_documents


def calculate_document_readiness_score(
    uploaded_doc_keys: list[str] | set[str] | tuple[str, ...],
    required_doc_keys: dict | list[str] | tuple[str, ...],
) -> dict[str, int | bool | list[dict[str, str | bool]]]:
    """Calculate document readiness from unique uploaded keys and requirements."""
    if isinstance(required_doc_keys, dict):
        required_documents = []
        for key, value in required_doc_keys.items():
            if isinstance(value, dict):
                required_documents.append({"key": key, **value})
            else:
                required_documents.append({
                    "key": key,
                    "label": str(value),
                    "requires_self_attestation": True,
                })
    else:
        required_documents = [
            {"key": key, "label": key.replace("_", " "), "requires_self_attestation": True}
            if isinstance(key, str)
            else key
            for key in required_doc_keys
        ]

    uploaded_keys = set(uploaded_doc_keys)
    required_documents_by_key = {document["key"]: document for document in required_documents}
    required_keys = set(required_documents_by_key)
    uploaded_required_keys = uploaded_keys & required_keys
    missing_documents = [
        {
            "key": document["key"],
            "label": document.get("label", document["key"].replace("_", " ")),
            "requires_self_attestation": document.get("requires_self_attestation", True),
        }
        for document in required_documents_by_key.values()
        if document["key"] not in uploaded_required_keys
    ]
    total_required = len(required_keys)
    total_uploaded = len(uploaded_required_keys)
    readiness_score = 100 if total_required == 0 else total_uploaded * 100 // total_required

    return {
        "readiness_score": readiness_score,
        "total_required": total_required,
        "total_uploaded": total_uploaded,
        "missing_documents": missing_documents,
        "is_ready_for_submission": readiness_score == 100,
    }


MONEY_FIELDS = (
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
)


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value)) if value is not None else Decimal("0")


def calculate_assessment(assessment: Any) -> dict[str, Any]:
    values = {field: _decimal(getattr(assessment, field)) for field in MONEY_FIELDS}

    total_cost = values["tuition"] + values["living_costs"]
    available_funding = (
        values["scholarships"]
        + values["savings"]
        + values["fees_paid"]
        + values["family_contribution"]
    )
    funding_gap = max(Decimal("0"), total_cost - available_funding)
    net_worth = values["assets"] - values["liabilities"] + values["income"]

    warnings = []
    if any(
        value < 0
        for value in values.values()
    ):
        raise ValidationError("Money values cannot be negative.")
    if not assessment.scholarships and not assessment.savings and not assessment.fees_paid:
        warnings.append("Missing required financial information: funding sources are not provided.")
    if not assessment.collateral_value:
        warnings.append("Collateral value is not provided; collateral-route eligibility cannot be assessed.")

    return {
        "total_study_cost": total_cost,
        "available_funding": available_funding,
        "funding_gap": funding_gap,
        "net_worth": net_worth,
        "collateral_value": values["collateral_value"],
        "warnings": warnings,
    }


def generate_lender_matches(lenders: list[dict[str, Any]], cibil_score: int, route: str, collateral_value: Decimal | int) -> list[dict[str, Any]]:
    normalized_route = route.lower()
    matches: list[dict[str, Any]] = []

    for lender in lenders:
        lender_route = str(lender.get("loan_type", "")).lower()
        if lender_route != normalized_route:
            continue

        minimum_cibil = lender.get("minimum_cibil")
        if minimum_cibil is not None and cibil_score < int(minimum_cibil):
            continue

        if normalized_route == "collateral" and collateral_value <= 0:
            continue

        lender_copy = dict(lender)
        lender_copy["interest_rate"] = lender_copy.get("interest_rate")
        matches.append(lender_copy)

    return matches
