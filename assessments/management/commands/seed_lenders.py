import json
from pathlib import Path

from django.core.management.base import BaseCommand

from assessments.models import Lender


class Command(BaseCommand):
    help = "Load the supplied lender reference dataset."

    def handle(self, *args, **options):
        source = Path(__file__).resolve().parents[3] / "lender_data.json"
        data = json.loads(source.read_text(encoding="utf-8"))

        created = 0
        for lender_data in data:
            lender, was_created = Lender.objects.update_or_create(
                name=lender_data["name"],
                loan_type=lender_data["loan_type"],
                defaults={
                    "interest_rate": str(lender_data["interest_rate"]),
                    "minimum_cibil": lender_data.get("minimum_cibil"),
                    "conditions": lender_data.get("conditions", ""),
                    "document_categories": lender_data.get("document_categories", []),
                },
            )
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Loaded {len(data)} lenders; created {created}."))
