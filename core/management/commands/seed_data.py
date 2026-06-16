import json
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import (
    Symptom, NodeSubscriptionPlan, HomeCard, DailyCheckinQuestion, DailyCheckinAnswer
)

User = get_user_model()

class Command(BaseCommand):
    help = "Seeds the database with mock data using Django's ORM."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting database seeding process..."))

        # Seed Symptoms
        self.stdout.write("Seeding symptoms...")
        if not Symptom.objects.exists():
            symptoms = [
                "Anger management",
                "Specific phobia",
                "Social anxiety",
                "Sleep difficulties",
                "Sexual abuse",
                "Past trauma",
                "Family conflict",
                "Low self-esteem"
            ]
            for sym in symptoms:
                Symptom.objects.create(title=sym, state_id=1, type_id=0)
            self.stdout.write(self.style.SUCCESS("  + Seeded symptoms."))
        else:
            self.stdout.write("  Symptoms already seeded.")

        # Seed Subscription Plans
        self.stdout.write("Seeding subscription plans...")
        if not NodeSubscriptionPlan.objects.exists():
            NodeSubscriptionPlan.objects.create(
                plan_name='Weekly Basic Plan',
                plan_description='Standard access to premium therapy services.',
                plan_weekly_price=500.00,
                plan_duration=7,
                total_price=500.00,
                doctor_price=350.00,
                no_of_free_trial_days=3,
                plan_type='weekly'
            )
            NodeSubscriptionPlan.objects.create(
                plan_name='Monthly Premium Plan',
                plan_description='Full 24/7 access to select therapists.',
                plan_weekly_price=1800.00,
                plan_duration=30,
                total_price=1800.00,
                doctor_price=1400.00,
                no_of_free_trial_days=7,
                plan_type='monthly'
            )
            self.stdout.write(self.style.SUCCESS("  + Seeded subscription plans."))
        else:
            self.stdout.write("  Subscription plans already seeded.")

        # Seed Home Cards
        self.stdout.write("Seeding home cards...")
        if not HomeCard.objects.exists():
            HomeCard.objects.create(
                title='Welcome to Spilbloo!',
                description='Start your mental health journey today with certified therapists.',
                img_url_path='/media/cards/welcome.png',
                is_active=1,
                position=1,
                card_type='info'
            )
            HomeCard.objects.create(
                title='Daily Check-in Reminder',
                description='Do not forget to complete your daily check-in to track progress.',
                img_url_path='/media/cards/checkin.png',
                is_active=1,
                position=2,
                card_type='alert'
            )
            self.stdout.write(self.style.SUCCESS("  + Seeded home cards."))
        else:
            self.stdout.write("  Home cards already seeded.")

        # Seed Daily Check-in Q&A
        self.stdout.write("Seeding daily check-in questions & answers...")
        if not DailyCheckinQuestion.objects.exists():
            DailyCheckinQuestion.objects.create(id=1, question='How are you feeling today?', is_active=1)
            DailyCheckinQuestion.objects.create(id=2, question='Did you sleep well last night?', is_active=1)

            DailyCheckinAnswer.objects.create(question_id=1, answer='Excellent')
            DailyCheckinAnswer.objects.create(question_id=1, answer='Good')
            DailyCheckinAnswer.objects.create(question_id=1, answer='Neutral')
            DailyCheckinAnswer.objects.create(question_id=1, answer='Bad')

            DailyCheckinAnswer.objects.create(question_id=2, answer='Yes')
            DailyCheckinAnswer.objects.create(question_id=2, answer='No')
            DailyCheckinAnswer.objects.create(question_id=2, answer='Somewhat')
            self.stdout.write(self.style.SUCCESS("  + Seeded daily check-in Q&A questions."))
        else:
            self.stdout.write("  Daily check-in questions already seeded.")

        # Seed Therapist Users
        self.stdout.write("Creating therapist users...")
        therapist_emails = ["therapist1@spilbloo.com", "therapist2@spilbloo.com"]
        for idx, email in enumerate(therapist_emails, start=1):
            if not User.objects.filter(email=email).exists():
                User.objects.create_user(
                    email=email,
                    password="Password@123",
                    full_name=f"Dr. Therapist {idx}",
                    role_id=5, # Doctor / Therapist
                    about_me="Dedicated licensed clinical therapist helping patients achieve mental well-being.",
                    contact_no=f"+91987654321{idx}",
                    qualification='Ph.D. in Clinical Psychology',
                    experience=8,
                    online='yes',
                    is_available=True,
                    token='mock_device_token'
                )
                self.stdout.write(self.style.SUCCESS(f"  + Created therapist user: {email}"))
            else:
                self.stdout.write(f"  Therapist user {email} already exists.")

        self.stdout.write(self.style.SUCCESS("Database seeding completed successfully!"))
