from django.contrib import admin

from .models import Assessment, Document, Lender


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ("id", "university", "course", "funding_gap", "route", "created_at")
    list_filter = ("route", "created_at")
    search_fields = ("country", "university", "course")

    def funding_gap(self, obj):
        return obj.tuition + obj.living_costs - (
            obj.scholarships + obj.savings + obj.fees_paid + obj.family_contribution
        )

    funding_gap.short_description = "Funding gap"


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("assessment", "document_type", "status", "uploaded_at")
    list_filter = ("document_type", "status")


@admin.register(Lender)
class LenderAdmin(admin.ModelAdmin):
    list_display = ("name", "loan_type", "interest_rate", "minimum_cibil")
    list_filter = ("name", "loan_type")
    search_fields = ("name", "conditions")
