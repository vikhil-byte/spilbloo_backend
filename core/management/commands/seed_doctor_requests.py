from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import DoctorRequest, DoctorReason

User = get_user_model()


class Command(BaseCommand):
    help = "Seeds the database with example doctor change requests."

    def handle(self, *args, **kwargs):
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stdout.write(self.style.ERROR("No admin user found. Please create an admin (superuser) first."))
            return

        # Try to reuse existing doctor reasons created by seed_doctor_reasons
        reason_map = {r.title: r for r in DoctorReason.objects.all()}

        def get_or_create_reason(title: str) -> DoctorReason:
            reason = reason_map.get(title)
            if reason:
                return reason
            reason, _ = DoctorReason.objects.get_or_create(title=title, defaults={"created_by": admin_user})
            reason_map[title] = reason
            return reason

        # Use some existing users as doctors/patients, fall back to admin if missing
        doctor_users = list(User.objects.filter(role_id=User.ROLE_DOCTER)[:5])
        patient_users = list(User.objects.exclude(id__in=[u.id for u in doctor_users])[:5])

        if not doctor_users:
            self.stdout.write(self.style.WARNING("No doctors found (role_id=ROLE_DOCTER). Using admin as doctor for seed data."))
            doctor_users = [admin_user]

        if not patient_users:
            self.stdout.write(self.style.WARNING("No patients/other users found. Using admin as patient for seed data."))
            patient_users = [admin_user]

        doctor_requests_seed = [
            {
                "reason_title": "Schedule conflict",
                "description": "Patient requested a different time slot due to schedule conflict.",
            },
            {
                "reason_title": "Patient request",
                "description": "Patient requested to change to a therapist with different specialization.",
            },
            {
                "reason_title": "Therapist was slow to respond",
                "description": "Patient reported delays in responses and requested change.",
            },
        ]

        created_count = 0
        for idx, seed in enumerate(doctor_requests_seed):
            reason = get_or_create_reason(seed["reason_title"])
            doctor = doctor_users[idx % len(doctor_users)]
            patient = patient_users[idx % len(patient_users)]

            doctor_request, created = DoctorRequest.objects.get_or_create(
                reason=reason,
                doctor=doctor,
                description=seed["description"],
                defaults={"created_by": admin_user},
            )

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created doctor request (reason='{reason.title}', doctor='{doctor.email}', patient='{patient.email}')"
                    )
                )
            else:
                self.stdout.write(
                    f"Doctor request already exists for reason='{reason.title}' and doctor='{doctor.email}'."
                )

        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {created_count} new doctor requests."))

