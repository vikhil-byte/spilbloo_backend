from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import EmergencyResource

User = get_user_model()


class Command(BaseCommand):
    help = "Seeds the database with sample emergency resources."

    def handle(self, *args, **kwargs):
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stdout.write(
                self.style.ERROR("No admin user found. Run seed_users or create a superuser first.")
            )
            return

        resources = [
            {
                "title": "National Emergency Helpline",
                "contact_no": "112",
                "alternate_contact_no": "",
                "link": "https://example.com/emergency",
                "timings": "24/7",
            },
            {
                "title": "Mental Health Crisis Line",
                "contact_no": "1800-123-4567",
                "alternate_contact_no": "1800-765-4321",
                "link": "",
                "timings": "24/7",
            },
            {
                "title": "Local Hospital Emergency",
                "contact_no": "+91-9876543210",
                "alternate_contact_no": "",
                "link": "",
                "timings": "24/7",
            },
        ]

        created_count = 0
        for r in resources:
            _, created = EmergencyResource.objects.get_or_create(
                title=r["title"],
                defaults={
                    "contact_no": r["contact_no"],
                    "alternate_contact_no": r.get("alternate_contact_no") or None,
                    "link": r.get("link") or None,
                    "timings": r.get("timings") or None,
                    "state_id": EmergencyResource.STATE_ACTIVE,
                    "created_by": admin_user,
                },
            )
            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Seeded {created_count} new emergency resources.")
        )
