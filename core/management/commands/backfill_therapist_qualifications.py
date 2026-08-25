from django.core.management.base import BaseCommand
from django.db.models import Q
from accounts.models import User
from core.models import TherapistApplication


class Command(BaseCommand):
    help = "Backfills missing therapist qualifications from TherapistApplication records."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without saving changes to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        if dry_run:
            self.stdout.write(self.style.WARNING("--- RUNNING IN DRY-RUN MODE (No DB changes) ---\n"))

        therapists = User.objects.filter(
            role_id=User.ROLE_DOCTER
        ).filter(
            Q(qualification__isnull=True) | Q(qualification="")
        ).order_by("id")

        total_missing = therapists.count()
        self.stdout.write(f"Found {total_missing} therapist(s) with missing qualifications.\n")

        if total_missing == 0:
            self.stdout.write(self.style.SUCCESS("All therapists already have qualifications set!"))
            return

        updated_count = 0
        skipped_count = 0

        for therapist in therapists:
            # 1. Match by email or created_by
            app = (
                TherapistApplication.objects.filter(email__iexact=therapist.email).order_by("-id").first()
                or TherapistApplication.objects.filter(created_by=therapist).order_by("-id").first()
            )

            if app and app.qualification:
                qual_value = app.qualification.strip()
                self.stdout.write(
                    f"Therapist ID {therapist.id} ({therapist.full_name or therapist.email}): "
                    f"Found qualification from Application ID {app.id} -> '{qual_value}'"
                )
                if not dry_run:
                    therapist.qualification = qual_value
                    therapist.save(update_fields=["qualification"])
                updated_count += 1
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"Therapist ID {therapist.id} ({therapist.full_name or therapist.email}): "
                        f"No qualification found in TherapistApplication table."
                    )
                )
                skipped_count += 1

        self.stdout.write("\n" + "=" * 60)
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Dry run complete. {updated_count} therapist(s) would be updated, {skipped_count} skipped."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Backfill complete. Successfully updated {updated_count} therapist(s). {skipped_count} skipped."
                )
            )
