import json
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import (
    Symptom, NodeSubscriptionPlan, HomeCard, DailyCheckinQuestion, DailyCheckinAnswer,
    DailyJournal, TherapistApplication, Language
)
from availability.models import Slot

User = get_user_model()

class Command(BaseCommand):
    help = "Seeds the database with mock data using Django's ORM."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting database seeding process..."))

        # Seed Symptoms
        self.stdout.write("Seeding symptoms...")
        symptoms = [
            "Depression & Anxiety",
            "Relationship & Marriage",
            "Stress & Burnout",
            "Trauma & Abuse",
            "Sleep Issues",
            "Addiction",
            "Parenting",
            "Women's Health",
            "OCD",
            "Bipolar Disorder",
            "Social Anxiety & Phobias",
            "Grief & Loss",
            "Sexual Wellness",
            "Academic & Career Stress",
            "Just Need Someone to Talk To",
        ]
        symptoms_seeded_count = 0
        for sym in symptoms:
            _, created = Symptom.objects.get_or_create(
                title=sym,
                defaults={'state_id': Symptom.STATE_ACTIVE, 'type_id': 0}
            )
            if created:
                symptoms_seeded_count += 1

        if symptoms_seeded_count > 0:
            self.stdout.write(self.style.SUCCESS(f"  + Seeded {symptoms_seeded_count} symptoms."))
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
        questions_data = [
            (1, "How was your relationship with your family?", "Relationship", 1),
            (2, "How often did you feel nervous, anxious, or on edge?", "Anxiety", 1),
            (3, "How would you rate your sleep quality last night?", "Sleep", 1),
            (4, "How would you describe your energy levels and motivation?", "Energy", 1),
            (5, "How would you rate your mood?", "Mood", 1),
            (8, "how are you?", None, 0),
        ]
        for q_id, q_text, q_title, q_active in questions_data:
            DailyCheckinQuestion.objects.update_or_create(
                id=q_id,
                defaults={
                    "question": q_text,
                    "title": q_title,
                    "is_active": q_active,
                }
            )

        answers_data = [
            (1, 1, "Energized", 5, 1),
            (2, 1, "Calm and steady", 4, 1),
            (3, 1, "Just getting", 3, 1),
            (4, 1, "Mentally drained", 2, 1),
            (5, 1, "Overwhelmed", 1, 1),
            (6, 2, "Fully refreshed", 5, 1),
            (7, 2, "Mostly fine, slight tiredness", 4, 1),
            (8, 2, "effort to function", 3, 1),
            (9, 2, "Felt sluggish most of the day", 2, 1),
            (10, 2, "Exhausted, could not focus properly", 1, 1),
            (11, 3, "Fully aligned, made strong progress", 5, 1),
            (12, 3, "Did a few meaningful things", 4, 1),
            (13, 3, "Stayed busy but not impactful", 3, 1),
            (14, 3, "Procrastinated more than I like", 2, 1),
            (15, 3, "Completely off-track today", 1, 1),
            (16, 4, "Present, engaged, and supportive", 5, 1),
            (17, 4, "Had some positive interactions", 4, 1),
            (18, 4, "neutral", 3, 1),
            (19, 4, "Distant or slightly irritable", 2, 1),
            (20, 4, "Conflict, regret, or disconnection", 1, 1),
            (21, 5, "Very intentional & nourishing", 5, 1),
            (22, 5, "Mostly mindful with a few slips", 4, 1),
            (23, 5, "Ate whatever was convenient", 3, 1),
            (24, 5, "emotional eating", 2, 1),
            (25, 5, "No control, unhealthy all day", 1, 1),
        ]
        for a_id, q_id, ans, score, jq_id in answers_data:
            DailyCheckinAnswer.objects.update_or_create(
                id=a_id,
                defaults={
                    "question_id": q_id,
                    "answer": ans,
                    "score": score,
                    "journal_question_id": jq_id,
                }
            )
        self.stdout.write(self.style.SUCCESS("  + Seeded daily check-in questions and answers."))

        # Seed 32 Time Slots
        self.stdout.write("Seeding time slots...")
        slots_data = [
            (1, "00:00:00", "00:45:00"), (2, "00:45:00", "01:30:00"), (3, "01:30:00", "02:15:00"), (4, "02:15:00", "03:00:00"),
            (5, "03:00:00", "03:45:00"), (6, "03:45:00", "04:30:00"), (7, "04:30:00", "05:15:00"), (8, "05:15:00", "06:00:00"),
            (9, "06:00:00", "06:45:00"), (10, "06:45:00", "07:30:00"), (11, "07:30:00", "08:15:00"), (12, "08:15:00", "09:00:00"),
            (13, "09:00:00", "09:45:00"), (14, "09:45:00", "10:30:00"), (15, "10:30:00", "11:15:00"), (16, "11:15:00", "12:00:00"),
            (17, "12:00:00", "12:45:00"), (18, "12:45:00", "13:30:00"), (19, "13:30:00", "14:15:00"), (20, "14:15:00", "15:00:00"),
            (21, "15:00:00", "15:45:00"), (22, "15:45:00", "16:30:00"), (23, "16:30:00", "17:15:00"), (24, "17:15:00", "18:00:00"),
            (25, "18:00:00", "18:45:00"), (26, "18:45:00", "19:30:00"), (27, "19:30:00", "20:15:00"), (28, "20:15:00", "21:00:00"),
            (29, "21:00:00", "21:45:00"), (30, "21:45:00", "22:30:00"), (31, "22:30:00", "23:15:00"), (32, "23:15:00", "23:59:59")
        ]
        for slot_id, s_time, e_time in slots_data:
            Slot.objects.update_or_create(
                id=slot_id,
                defaults={
                    "title": "Slot",
                    "start_time": s_time,
                    "end_time": e_time,
                    "state_id": 1,
                }
            )
        self.stdout.write(self.style.SUCCESS("  + Seeded 32 time slots."))

        # Seed Daily Journals (mapped to admin user)
        admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
        if admin_user:
            self.stdout.write(f"Seeding daily journals (assigned to admin user {admin_user.email})...")
            journals_data = [
                (1, "2023-09-13", "this is for testing edit API.", 1),
                (2, "2026-06-22", "Hello i ma good today", 1),
                (3, "2023-09-21", "this is for testing timezone.", 1),
                (4, "2026-06-22", "Okay okay", 1),
                (5, "2026-06-22", "Hello", 1),
                (6, "2023-09-15", "Testing entry date edit API .", 1),
                (7, "2026-04-23", "Hello i am good.", 1),
                (8, "2026-04-24", "I am doing well today. Wow", 1),
                (9, "2026-04-26", "I am doing good. Nice day.", 1),
                (10, "2026-05-12", "Test ", 1),
                (11, "2026-06-28", "Hello chinmay", 1),
                (12, "2026-06-28", "Okay okay", 1),
                (13, "2026-06-26", "I am okay okay okay", 1),
                (14, "2026-06-29", "Hello I am good", 1),
                (15, "2026-06-23", "Okay okay", 1),
                (16, "2026-07-06", "Test note.", 1),
                (17, "2026-07-07", "Test journey.", 1),
                (18, "2026-07-17", "Test note", 1),
                (19, "2026-07-19", "Doing good today", 1),
                (20, "2025-07-22", "hiiiii", 1),
                (21, "2025-10-23", "Test journal.", 1),
                (22, "2026-07-23", "Test note. Test note 2.", 1),
                (23, "2026-07-23", "Note 1", 1),
                (24, "2026-07-24", "thgffgvg", 1),
                (25, "2026-07-26", "Fgvjhkj cjjk Bhuj I", 1),
                (26, "2026-07-27", "Hdjsj", 1),
                (27, "2026-07-27", "Hchcjc", 1),
                (28, "2026-07-28", "Today felt lighter than yesterday.\nI still caught myself overthinking\na few conversations, but instead of\nspiralling, I took a walk and let\nmyself breathe.\n\nI'm learning that healing isn't\nabout having perfect days—it's\nabout showing up for myself,\none small step at a time.\n\nTonight, I'm choosing progress\nover perfection.\n\n😊 Calm", 1),
            ]
            for j_id, e_date, j_text, q_id in journals_data:
                DailyJournal.objects.update_or_create(
                    id=j_id,
                    defaults={
                        "entry_date": e_date,
                        "journal": j_text,
                        "question_id": q_id,
                        "created_by": admin_user,
                    }
                )
            self.stdout.write(self.style.SUCCESS("  + Seeded daily journals."))

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
        # Seed Indian Languages
        self.stdout.write("Seeding Indian languages...")
        languages = [
            ("English", "en"),
            ("Hindi", "hi"),
            ("Bengali", "bn"),
            ("Marathi", "mr"),
            ("Telugu", "te"),
            ("Tamil", "ta"),
            ("Gujarati", "gu"),
            ("Urdu", "ur"),
            ("Kannada", "kn"),
            ("Odia", "or"),
            ("Malayalam", "ml"),
            ("Punjabi", "pa"),
            ("Assamese", "as"),
            ("Maithili", "mai"),
            ("Santali", "sat"),
            ("Kashmiri", "ks"),
            ("Nepali", "ne"),
            ("Konkani", "kok"),
            ("Dogri", "doi"),
            ("Manipuri", "mni"),
            ("Bodo", "brx"),
            ("Sanskrit", "sa"),
            ("Sindhi", "sd"),
            ("Bhojpuri", "bho"),
            ("Marwari", "mwr"),
            ("Tulu", "tcy"),
            ("Chhattisgarhi", "hne"),
        ]
        langs_seeded_count = 0
        for lang_name, lang_code in languages:
            _, created = Language.objects.get_or_create(
                name=lang_name,
                defaults={'code': lang_code, 'state_id': Language.STATE_ACTIVE}
            )
            if created:
                langs_seeded_count += 1

        if langs_seeded_count > 0:
            self.stdout.write(self.style.SUCCESS(f"  + Seeded {langs_seeded_count} Indian languages."))
        else:
            self.stdout.write("  Indian languages already seeded.")

        self.stdout.write(self.style.SUCCESS("Database seeding completed successfully!"))
