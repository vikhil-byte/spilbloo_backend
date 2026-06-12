import json
from django.core.management.base import BaseCommand
from django.db import connection
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = "Seeds the database with mock data and sets up legacy raw-SQL compatibility tables."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting database seeding process..."))

        # 1. Alter tbl_user to add legacy columns if they don't exist
        self.stdout.write("Checking and adding legacy fields to tbl_user...")
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE tbl_user ADD COLUMN IF NOT EXISTS qualification VARCHAR(255);")
            cursor.execute("ALTER TABLE tbl_user ADD COLUMN IF NOT EXISTS experience INTEGER DEFAULT 0;")
            cursor.execute("ALTER TABLE tbl_user ADD COLUMN IF NOT EXISTS online VARCHAR(50) DEFAULT 'no';")
            cursor.execute("ALTER TABLE tbl_user ADD COLUMN IF NOT EXISTS is_available BOOLEAN DEFAULT TRUE;")
            cursor.execute("ALTER TABLE tbl_user ADD COLUMN IF NOT EXISTS token VARCHAR(255) DEFAULT '';")

        # 2. Create missing raw-SQL tables
        self.stdout.write("Creating missing legacy tables...")
        with connection.cursor() as cursor:
            # tbl_home_card
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tbl_home_card (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(255),
                    description TEXT,
                    img_url_path VARCHAR(255),
                    is_active INTEGER DEFAULT 1,
                    position INTEGER DEFAULT 0,
                    card_type VARCHAR(50)
                );
            """)

            # tbl_daily_journal
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tbl_daily_journal (
                    id SERIAL PRIMARY KEY,
                    entry_date DATE DEFAULT CURRENT_DATE,
                    journal TEXT,
                    question_id INTEGER,
                    created_by_id INTEGER
                );
            """)

            # tbl_daily_checkin_question
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tbl_daily_checkin_question (
                    id SERIAL PRIMARY KEY,
                    question TEXT,
                    is_active INTEGER DEFAULT 1
                );
            """)

            # tbl_daily_checkin_answer
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tbl_daily_checkin_answer (
                    id SERIAL PRIMARY KEY,
                    question_id INTEGER,
                    answer TEXT
                );
            """)

            # tbl_daily_checkin_question_and_answer
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tbl_daily_checkin_question_and_answer (
                    id SERIAL PRIMARY KEY,
                    created_by_id INTEGER,
                    qna_map JSONB,
                    entry_date DATE DEFAULT CURRENT_DATE
                );
            """)

            # tbl_user_app_review
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tbl_user_app_review (
                    id SERIAL PRIMARY KEY,
                    rating INTEGER,
                    review TEXT,
                    created_by_id INTEGER
                );
            """)

            # tbl_chats_history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tbl_chats_history (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER,
                    chats_message TEXT,
                    created_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # tbl_user_selected_therapist_plan
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tbl_user_selected_therapist_plan (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    therapist_id BIGINT,
                    plan_id BIGINT,
                    selected_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # tbl_subscription_plan
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tbl_subscription_plan (
                    id SERIAL PRIMARY KEY,
                    plan_name VARCHAR(255),
                    plan_description TEXT,
                    plan_weekly_price DECIMAL(10, 2),
                    plan_duration INTEGER,
                    total_price DECIMAL(10, 2),
                    doctor_price DECIMAL(10, 2),
                    no_of_free_trial_days INTEGER,
                    plan_type VARCHAR(50)
                );
            """)

            # tbl_api_access_token
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tbl_api_access_token (
                    id SERIAL PRIMARY KEY,
                    created_by_id INTEGER,
                    device_token VARCHAR(255)
                );
            """)

        # 3. Seed initial / mock data
        self.stdout.write("Seeding data into tables...")

        # Seed Symptoms
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM tbl_symptom;")
            if cursor.fetchone()[0] == 0:
                symptoms = ["Anger management", "Specific phobia", "Social anxiety", "Sleep difficulties", "Sexual abuse", "Past trauma", "Family conflict", "Low self-esteem"]
                for sym in symptoms:
                    cursor.execute("INSERT INTO tbl_symptom (title, state_id, type_id, created_on) VALUES (%s, 1, 0, NOW());", [sym])
                self.stdout.write(self.style.SUCCESS("  + Seeded symptoms."))

        # Seed Subscription Plans
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM tbl_subscription_plan;")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO tbl_subscription_plan (plan_name, plan_description, plan_weekly_price, plan_duration, total_price, doctor_price, no_of_free_trial_days, plan_type)
                    VALUES 
                    ('Weekly Basic Plan', 'Standard access to premium therapy services.', 500.00, 7, 500.00, 350.00, 3, 'weekly'),
                    ('Monthly Premium Plan', 'Full 24/7 access to select therapists.', 1800.00, 30, 1800.00, 1400.00, 7, 'monthly');
                """)
                self.stdout.write(self.style.SUCCESS("  + Seeded subscription plans."))

        # Seed Home Cards
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM tbl_home_card;")
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO tbl_home_card (title, description, img_url_path, is_active, position, card_type)
                    VALUES 
                    ('Welcome to Spilbloo!', 'Start your mental health journey today with certified therapists.', '/media/cards/welcome.png', 1, 1, 'info'),
                    ('Daily Check-in Reminder', 'Do not forget to complete your daily check-in to track progress.', '/media/cards/checkin.png', 1, 2, 'alert');
                """)
                self.stdout.write(self.style.SUCCESS("  + Seeded home cards."))

        # Seed Daily Check-in Q&A
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM tbl_daily_checkin_question;")
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO tbl_daily_checkin_question (id, question, is_active) VALUES (1, 'How are you feeling today?', 1);")
                cursor.execute("INSERT INTO tbl_daily_checkin_question (id, question, is_active) VALUES (2, 'Did you sleep well last night?', 1);")
                
                cursor.execute("INSERT INTO tbl_daily_checkin_answer (question_id, answer) VALUES (1, 'Excellent'), (1, 'Good'), (1, 'Neutral'), (1, 'Bad');")
                cursor.execute("INSERT INTO tbl_daily_checkin_answer (question_id, answer) VALUES (2, 'Yes'), (2, 'No'), (2, 'Somewhat');")
                self.stdout.write(self.style.SUCCESS("  + Seeded daily check-in Q&A questions."))

        # Seed Therapist Users
        self.stdout.write("Creating therapist users...")
        therapist_emails = ["therapist1@spilbloo.com", "therapist2@spilbloo.com"]
        for idx, email in enumerate(therapist_emails, start=1):
            if not User.objects.filter(email=email).exists():
                user = User.objects.create_user(
                    email=email,
                    password="Password@123",
                    full_name=f"Dr. Therapist {idx}",
                    role_id=5, # Doctor / Therapist
                    about_me="Dedicated licensed clinical therapist helping patients achieve mental well-being.",
                    contact_no=f"+91987654321{idx}"
                )
                # Add raw columns details
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE tbl_user 
                        SET qualification = 'Ph.D. in Clinical Psychology', experience = 8, online = 'yes', is_available = TRUE, token = 'mock_device_token'
                        WHERE id = %s;
                    """, [user.id])
                self.stdout.write(self.style.SUCCESS(f"  + Created therapist user: {email}"))

        self.stdout.write(self.style.SUCCESS("Database seeding completed successfully!"))
