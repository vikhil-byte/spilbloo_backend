from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from core.models import Feed


User = get_user_model()


class Command(BaseCommand):
    help = "Seeds the database with sample Feed entries for testing the admin Feeds page."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=50,
            help="Number of Feed records to create (default: 50)",
        )

    def handle(self, *args, **options):
        count = options["count"]

        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stdout.write(
                self.style.ERROR("No admin user found. Please create one first.")
            )
            return

        created = 0
        for i in range(count):
            feed = Feed.objects.create(
                content=f"Seeded test feed #{i + 1}",
                model_type="SeedTest",
                model_id=i + 1,
                user_ip="127.0.0.1",
                user_agent="seed_feeds/1.0",
                created_by=admin_user,
            )
            created += 1
            self.stdout.write(
                self.style.SUCCESS(f"Created feed entry ID={feed.id} ({feed.content})")
            )

        self.stdout.write(
            self.style.SUCCESS(f"Successfully seeded {created} feed entries.")
        )

