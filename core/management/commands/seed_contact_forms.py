from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import ContactForm

User = get_user_model()


class Command(BaseCommand):
    help = "Seeds the database with sample therapist applications (contact forms)."

    def handle(self, *args, **kwargs):
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stdout.write(
                self.style.ERROR("No admin user found. Run seed_users or create a superuser first.")
            )
            return

        applications = [
            {
                "name": "Dr. Priya Sharma",
                "email": "priya.therapist@example.com",
                "contact_no": "+91-9876543210",
                "city": "Mumbai",
                "country_code": "+91",
                "experience": "5 years",
                "state_id": ContactForm.STATE_INACTIVE,
            },
            {
                "name": "Dr. Rajesh Kumar",
                "email": "rajesh.k@example.com",
                "contact_no": "+91-9123456789",
                "city": "Delhi",
                "country_code": "+91",
                "experience": "3 years",
                "state_id": ContactForm.STATE_ACCEPT,
            },
            {
                "name": "Dr. Anjali Mehta",
                "email": "anjali.m@example.com",
                "contact_no": "+91-9988776655",
                "city": "Bangalore",
                "country_code": "+91",
                "experience": "7 years",
                "state_id": ContactForm.STATE_ACCEPT,
            },
        ]

        created_count = 0
        for app in applications:
            _, created = ContactForm.objects.get_or_create(
                email=app["email"],
                defaults={
                    "name": app["name"],
                    "contact_no": app.get("contact_no"),
                    "city": app.get("city"),
                    "country_code": app.get("country_code"),
                    "experience": app.get("experience"),
                    "state_id": app.get("state_id", ContactForm.STATE_INACTIVE),
                    "created_by": admin_user,
                },
            )
            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Seeded {created_count} new therapist applications.")
        )
