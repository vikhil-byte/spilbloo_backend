from django.core.management.base import BaseCommand
from core.models import Symptom
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds the database with common symptoms'

    def handle(self, *args, **kwargs):
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stdout.write(self.style.ERROR("No admin user found. Please create one first."))
            return

        common_symptoms = [
            "Anxiety",
            "Depression",
            "Stress",
            "ADHD",
            "Insomnia",
            "Trauma & PTSD",
            "Obsessive Compulsive Disorder (OCD)",
            "Panic Attacks",
            "Social Anxiety",
            "Bipolar Disorder",
            "Eating Disorders",
            "Relationship Issues",
            "Anger Management",
            "Grief & Loss",
            "Self-Esteem Issues"
        ]

        count = 0
        for title in common_symptoms:
            symptom, created = Symptom.objects.get_or_create(
                title=title,
                defaults={'created_by': admin_user}
            )
            if created:
                count += 1
                self.stdout.write(self.style.SUCCESS(f"Created symptom: {title}"))
            else:
                self.stdout.write(f"Symptom already exists: {title}")
        
        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {count} new symptoms."))
