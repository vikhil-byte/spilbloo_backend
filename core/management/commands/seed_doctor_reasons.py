from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import DoctorReason

User = get_user_model()


class Command(BaseCommand):
    help = "Seeds the database with common doctor reasons (change therapist reasons)."

    def handle(self, *args, **kwargs):
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stdout.write(self.style.ERROR("No admin user found. Please create an admin (superuser) first."))
            return

        reasons = [
            "Schedule conflict",
            "Patient request",
            "Therapist was slow to respond",
        ]

        created_count = 0
        for title in reasons:
            reason, created = DoctorReason.objects.get_or_create(
                title=title,
                defaults={"created_by": admin_user},
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"Created doctor reason: {title}"))
            else:
                self.stdout.write(f"Doctor reason already exists: {title}")

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {created_count} new doctor reasons."))

