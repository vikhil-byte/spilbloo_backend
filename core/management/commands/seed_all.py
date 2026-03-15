from django.core.management import call_command
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Runs all database seeding commands'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.MIGRATE_HEADING("Starting master seed process..."))
        
        # Add all seeding commands here
        commands = [
            ('seed_users', "Seeding users..."),
            ('seed_symptoms', "Seeding symptoms..."),
            ('seed_doctor_reasons', "Seeding doctor reasons..."),
            ('seed_doctor_requests', "Seeding doctor change requests..."),
            ('seed_emergency_resources', "Seeding emergency resources..."),
            ('seed_contact_forms', "Seeding therapist applications (contact forms)..."),
            ('seed_bookings', "Seeding bookings..."),
            ('seed_therapist_earnings', "Seeding therapist earnings..."),
        ]

        for cmd, message in commands:
            self.stdout.write(self.style.NOTICE(message))
            try:
                call_command(cmd)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error running {cmd}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS("\nMaster seed process completed!"))
