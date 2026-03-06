"""
Seed the database with mock users (admin, patients, therapists).
Usage: python manage.py seed_users

Default password for all seed users: seedpass123
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from accounts.models import User

SEED_PASSWORD = "seedpass123"


def make_user(email, full_name, role_id, **kwargs):
    """Create or update user; set password only on create."""
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            "full_name": full_name,
            "role_id": role_id,
            "state_id": User.STATE_ACTIVE,
            **kwargs,
        },
    )
    if created:
        user.set_password(SEED_PASSWORD)
        user.save()
    else:
        for k, v in kwargs.items():
            if hasattr(user, k):
                setattr(user, k, v)
        user.full_name = full_name
        user.role_id = role_id
        user.state_id = User.STATE_ACTIVE
        user.save()
    return user, created


class Command(BaseCommand):
    help = "Load mock users (admin, patients, therapists). Default password: seedpass123"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete only seed users (same emails as in this script) before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        seed_emails = [
            "admin@spilbloo.com",
            "alice@example.com",
            "bob@example.com",
            "carol@example.com",
            "david@example.com",
            "eve@example.com",
            "dr.john@spilbloo.com",
            "dr.jane@spilbloo.com",
        ]

        if options["clear"]:
            deleted = User.objects.filter(email__in=seed_emails).delete()
            count = deleted[0] if isinstance(deleted, tuple) else 0
            self.stdout.write(self.style.WARNING(f"Removed {count} seed user(s)."))
            return

        users_data = [
            # admin (for admin panel login)
            {
                "email": "admin@spilbloo.com",
                "full_name": "Admin User",
                "role_id": User.ROLE_ADMIN,
                "is_staff": True,
                "is_superuser": True,
            },
            # patients
            {
                "email": "alice@example.com",
                "full_name": "Alice Smith",
                "role_id": User.ROLE_PATIENT,
                "contact_no": "+1234567890",
                "timezone": "Asia/Kolkata",
            },
            {
                "email": "bob@example.com",
                "full_name": "Bob Jones",
                "role_id": User.ROLE_PATIENT,
                "contact_no": "+1234567891",
                "timezone": "Asia/Kolkata",
            },
            {
                "email": "carol@example.com",
                "full_name": "Carol White",
                "role_id": User.ROLE_PATIENT,
                "contact_no": "+1234567892",
                "timezone": "Asia/Kolkata",
            },
            {
                "email": "david@example.com",
                "full_name": "David Brown",
                "role_id": User.ROLE_PATIENT,
                "contact_no": "+1234567893",
                "timezone": "UTC",
            },
            {
                "email": "eve@example.com",
                "full_name": "Eve Davis",
                "role_id": User.ROLE_PATIENT,
                "contact_no": "+1234567894",
                "timezone": "Asia/Kolkata",
            },
            # therapists
            {
                "email": "dr.john@spilbloo.com",
                "full_name": "Dr. John Doe",
                "role_id": User.ROLE_DOCTER,
                "contact_no": "+919876543210",
                "city": "Mumbai",
                "timezone": "Asia/Kolkata",
            },
            {
                "email": "dr.jane@spilbloo.com",
                "full_name": "Dr. Jane Smith",
                "role_id": User.ROLE_DOCTER,
                "contact_no": "+919876543211",
                "city": "Bengaluru",
                "timezone": "Asia/Kolkata",
            },
        ]

        created_count = 0
        for data in users_data:
            email = data.pop("email")
            full_name = data.pop("full_name")
            role_id = data.pop("role_id")
            user, created = make_user(email, full_name, role_id, **data)
            if created:
                created_count += 1
                self.stdout.write(f"  Created: {email} ({full_name})")
            else:
                self.stdout.write(f"  Updated: {email} ({full_name})")

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {created_count} new user(s), {len(users_data) - created_count} updated. "
                f"Password for all: {SEED_PASSWORD}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS("Admin login: admin@spilbloo.com / seedpass123")
        )
