from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from core.models import TherapistEarning

User = get_user_model()


class Command(BaseCommand):
    help = "Seeds the database with mock therapist earnings (Therapists Earnings page)."

    def handle(self, *args, **options):
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stdout.write(
                self.style.ERROR("No admin user found. Run seed_users or create a superuser first.")
            )
            return

        doctors = list(User.objects.filter(role_id=User.ROLE_DOCTER)[:5])
        patients = list(User.objects.exclude(role_id=User.ROLE_DOCTER).exclude(is_superuser=True)[:5])

        if not doctors:
            self.stdout.write(
                self.style.WARNING("No doctors found. Using admin as therapist for seed earnings.")
            )
            doctors = [admin_user]
        if not patients:
            self.stdout.write(
                self.style.WARNING("No patients found. Using admin as patient for seed earnings.")
            )
            patients = [admin_user]

        amounts = ["500.00", "750.50", "1200.00", "600.00", "900.00", "1100.00"]
        mimblu = ["400.00", "600.40", "960.00", "480.00", "720.00", "880.00"]

        created_count = 0
        base_date = timezone.now() - timedelta(days=30)
        for idx in range(12):
            therapist = doctors[idx % len(doctors)]
            patient = patients[idx % len(patients)]
            earn_date = base_date + timedelta(days=idx * 2)
            amount = amounts[idx % len(amounts)]
            mimblu_earning = mimblu[idx % len(mimblu)]

            _, created = TherapistEarning.objects.get_or_create(
                therapist=therapist,
                patient=patient,
                date=earn_date,
                defaults={
                    "amount": amount,
                    "mimblu_earning": mimblu_earning,
                    "completed_booking": 1,
                    "state_id": TherapistEarning.STATE_ACTIVE,
                    "type_id": (TherapistEarning.TYPE_SUBSCRIPTION_PLAN if idx % 2 == 0 else TherapistEarning.TYPE_VIDEO_PLAN),
                    "created_by": admin_user,
                },
            )
            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Seeded {created_count} new therapist earnings.")
        )
