from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from availability.models import SlotBooking, DoctorSlot

User = get_user_model()


class Command(BaseCommand):
    help = "Seeds the database with mock slot bookings (Bookings page)."

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
                self.style.WARNING("No doctors found. Using admin as doctor for seed bookings.")
            )
            doctors = [admin_user]
        if not patients:
            self.stdout.write(
                self.style.WARNING("No patients found. Using admin as patient for seed bookings.")
            )
            patients = [admin_user]

        # Create a few doctor slots so we have valid slot_ids (optional; SlotBooking only needs slot_id int)
        created_slots = []
        for doc in doctors[:3]:
            for i in range(2):
                start = timezone.now() + timedelta(days=i * 7, hours=10)
                end = start + timedelta(hours=1)
                slot, created = DoctorSlot.objects.get_or_create(
                    created_by=doc,
                    availability_slot_id=doc.id * 10 + i,
                    defaults={
                        "start_time": start,
                        "end_time": end,
                        "state_id": 1,
                    },
                )
                if created:
                    created_slots.append(slot)

        # state_id: 2=REQUEST, 3=ACCEPT, 4=CANCELLED
        booking_seeds = [
            {"state_id": 3, "type_id": 1},
            {"state_id": 2, "type_id": 1},
            {"state_id": 3, "type_id": 2},
            {"state_id": 4, "type_id": 1},
            {"state_id": 3, "type_id": 1},
            {"state_id": 2, "type_id": 2},
        ]

        base_time = timezone.now() - timedelta(days=7)
        created_count = 0
        for idx, opts in enumerate(booking_seeds):
            doctor = doctors[idx % len(doctors)]
            patient = patients[idx % len(patients)]
            slot_id = (doctor.id * 10 + (idx % 3)) if created_slots else (idx + 1)
            start = base_time + timedelta(days=idx, hours=9 + (idx % 5))
            end = start + timedelta(hours=1)

            _, created = SlotBooking.objects.get_or_create(
                slot_id=slot_id,
                start_time=start,
                end_time=end,
                doctor_id=doctor.id,
                created_by=patient,
                defaults={
                    "state_id": opts["state_id"],
                    "type_id": opts["type_id"],
                    "is_active": 1 if opts["state_id"] == 3 else 0,
                },
            )
            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Seeded {created_count} new bookings (total slot bookings in DB).")
        )
