import json
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import (
    Symptom, NodeSubscriptionPlan, HomeCard, DailyCheckinQuestion, DailyCheckinAnswer,
    TherapistApplication
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

        # Seed Therapist Applications
        self.stdout.write("Seeding therapist applications...")
        if not TherapistApplication.objects.exists():
            TherapistApplication.objects.create(
                name='Dr. Aarav Mehta',
                email='aarav.mehta@example.com',
                contact_no='+919876543210',
                address='Flat 402, Green Glen Layout, Bellandur, Bengaluru',
                experience='5 years',
                qualification="Master's Degree (Psychology)",
                rci_registered='Yes',
                employment_status='Self-employed / Private Practice',
                modalities='Cognitive Behavioral Therapy (CBT), Trauma-Informed Care',
                hours_available='20-30 hours',
                days_available='Flexible (All days)',
                motivation='I want to reach more people and provide convenient online counseling through Spilbloo.',
                distress_situation='A client reached out in high distress. I acknowledged their feelings, slowed the conversation down, and guided them using calming ground techniques.',
                linkedin_profile='https://linkedin.com/in/aaravmehta',
                state_id=0, # New
            )
            TherapistApplication.objects.create(
                name='Pooja Sharma',
                email='pooja.sharma@example.com',
                contact_no='+919999888777',
                address='742 Evergreen Terrace, Mumbai',
                experience='3 years',
                qualification='M.Phil in Clinical Psychology',
                rci_registered='Yes',
                employment_status='Employed Full-time',
                modalities='Acceptance and Commitment Therapy (ACT), Dialectical Behavior Therapy (DBT)',
                hours_available='10-20 hours',
                days_available='Weekends only',
                motivation='Interested in working with a platform that values professional supervision and high-quality telehealth care.',
                distress_situation='Used empathetic validation and crisis-escalation screening protocols in text format to ensure safety.',
                linkedin_profile='https://linkedin.com/in/poojasharma',
                state_id=1, # Accept
            )
            TherapistApplication.objects.create(
                name='Vikram Singh',
                email='vikram.singh@example.com',
                contact_no='+919876543219',
                address='Park Avenue, Block C, Delhi',
                experience='Less than 1 year',
                qualification="Bachelor's Degree",
                rci_registered='No',
                employment_status='Not currently employed',
                modalities='Cognitive Behavioral Therapy (CBT)',
                hours_available='30-40 hours',
                days_available='Weekdays only',
                motivation='Looking to start my professional journey in a supportive remote counseling environment.',
                distress_situation='Helped client identify stressors and construct a self-care list during a challenging period.',
                state_id=2, # Reject
            )
            self.stdout.write(self.style.SUCCESS("  + Seeded therapist applications."))
        else:
            self.stdout.write("  Therapist applications already seeded.")

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
