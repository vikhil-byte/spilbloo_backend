import json
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import (
    Symptom, NodeSubscriptionPlan, HomeCard, DailyCheckinQuestion, DailyCheckinAnswer,
    DailyJournal, TherapistApplication, Language, Category, Faq
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

        # Seed FAQ Categories and FAQs
        self.stdout.write("Seeding FAQ categories & FAQs...")
        categories_data = [
            (1, 'General', 1),
            (2, 'Text & Video', 1),
            (3, 'Account & Privacy', 1),
            (4, 'Subscriptions & Billing', 1),
            (5, 'Therapist FAQs', 2),
        ]
        for cat_id, cat_title, type_id in categories_data:
            Category.objects.get_or_create(
                id=cat_id,
                defaults={'title': cat_title, 'state_id': Category.STATE_ACTIVE, 'type_id': type_id}
            )

        faqs_data = [
            {'id': 1, 'question': 'What is Spilbloo?', 'answer': '<p>Spilbloo is a text and video therapy platform that helps connect you with the right professional therapist. Text, share voice notes or schedule video calls, all on the app, and as per your convenience with a therapist that you select.</p>\n', 'category_id': 1},
            {'id': 2, 'question': 'Who is Spilbloo for?', 'answer': '<p>Spilbloo is for everyone who needs it. Spilbloo is for everyone across the race, gender and sexuality spectrum. Our goal is to make mental healthcare more accessible than it currently is.</p>\n', 'category_id': 1},
            {'id': 3, 'question': 'Who are the therapists on Spilbloo?', 'answer': '<p>All therapists on Spilbloo are clinical Mental Health Professionals (MHPs) who have completed their education of at least a post-graduate level typically as MA / MSc (Clinical or Counselling Psychology) and/or MPhil (Clinical Psychology). They deal with different fields of psychology, each with their own expertise.</p>\n', 'category_id': 1},
            {'id': 4, 'question': 'How much does it cost?', 'answer': '<p>Spilbloo has various subscription plans ranging from INR 499 to INR 699 per week. Our goal is to make quality mental healthcare affordable across the spectrum. To put that into perspective, Spilbloo is up to 5 times cheaper than in-person therapy.</p>\n', 'category_id': 1},
            {'id': 5, 'question': 'Is Spilbloo for emergency or SOS cases?', 'answer': '<p>No, Spilbloo is not for emergency, life-threatening or SOS cases. If you find yourself or someone you know in such a situation, please click on this link to use these third-party resources.</p>\n', 'category_id': 1},
            {'id': 6, 'question': 'Do I choose the therapist myself?', 'answer': '<p>Yes, our algorithm matches you with multiple options of therapists who are best suited to work with you. You select who you would like to speak with.</p>\n', 'category_id': 1},
            {'id': 7, 'question': 'What if I’m not happy with my therapist on Spilbloo?', 'answer': '<p>In case\xa0you are not happy with your current therapist, you can switch to a different one once during each subscription cycle. To do so, you can find the option under your \'Profile\'.</p>\n', 'category_id': 1},
            {'id': 8, 'question': 'What platforms is Spilbloo available on?', 'answer': '<p>Spilbloo is available on the iOS App Store and the Google Play Store.</p>\n', 'category_id': 1},
            {'id': 9, 'question': 'How do I communicate with the therapist?', 'answer': '<p>You can text and share voice notes with your therapist. Depending on the plan you have purchased, you can also schedule video sessions with them.</p>\n', 'category_id': 2},
            {'id': 10, 'question': 'How do I schedule video sessions?', 'answer': '<p>Tap on Book New Session on the Home screen. From there you can see the availability of your therapist by selecting the date. Once you select a time and book the session, the therapist will soon confirm.</p>\n', 'category_id': 2},
            {'id': 11, 'question': 'Can I take my video calls on the desktop or web?', 'answer': '<p>No, as of now you can only connect via the app.</p>\n', 'category_id': 2},
            {'id': 12, 'question': 'What happens if I need to reschedule my video session?', 'answer': '<p>To reschedule a session, tap on the 3 dots on the right of your scheduled session on the Home Screen. There you will be able to reschedule the session to a different time of your choosing. Sessions can only be rescheduled up to 24 hours prior to the commencement of the session.</p>\n', 'category_id': 2},
            {'id': 13, 'question': 'If I switch therapists, do I have access to the old messages?', 'answer': '<p>Yes. The chats still remain as an archive on your Chats tab.</p>\n', 'category_id': 2},
            {'id': 14, 'question': 'What personal information of mine does the therapist have access to?', 'answer': '<p>The therapist has no access to your contact information or full name. For example, if your name is Jay Malhotra, they can only see your contact as &lsquo;Jay M&rsquo;.</p>\n', 'category_id': 3},
            {'id': 15, 'question': 'Does client-therapist confidentiality apply to text-based therapy?', 'answer': '<p>Yes, your chats are secure and confidential on the Spilbloo app.</p>\n', 'category_id': 3},
            {'id': 16, 'question': 'Do I have the option of adding a passcode to access the app?', 'answer': '<p>Yes, you can add a passcode to the app. The option is available under &lsquo;Profile&rsquo;.</p>\n', 'category_id': 3},
            {'id': 17, 'question': 'Do you offer a free trial?', 'answer': '<p>Yes, all our subscription plans have a 7-day trial when you first subscribe.</p>\n', 'category_id': 4},
            {'id': 18, 'question': 'What happens if I don’t want to continue after the trial?', 'answer': '<p>Simple, you cancel your subscription before your trial ends. You will not be charged anything for this period.</p>\n', 'category_id': 4},
            {'id': 19, 'question': 'What is the duration of the subscription?', 'answer': '<p>We have different plans ranging from 30 day to 90 day periods. All subscriptions work on auto-renewal basis.</p>\n', 'category_id': 4},
            {'id': 20, 'question': 'When do I get charged?', 'answer': '<p>Your first charge will be at the end of the free trial. After that, all our plans auto-renew as per the duration of the plan purchased.</p>\n', 'category_id': 4},
            {'id': 21, 'question': 'How do I cancel my subscription?', 'answer': '<p>You can cancel your subscription under the &lsquo;Manage Subscription&rsquo; option in your Profile.</p>\n', 'category_id': 4},
            {'id': 22, 'question': 'Can I change my subscription?', 'answer': '<p>You can change your subscription under the &lsquo;Manage Subscription&rsquo; option in your Profile. However, your new subscription plan will only go into effect once the current plan ends.</p>\n', 'category_id': 4},
            {'id': 23, 'question': 'Can I purchase additional video sessions with my therapist?', 'answer': '<p>Yes, you can purchase additional video sessions</p>\n', 'category_id': 4},
            {'id': 24, 'question': 'Can I use my insurance to cover the subscription fees?', 'answer': '<p>No, Spilbloo does not support any insurance providers as of now.</p>\n', 'category_id': 4},
            {'id': 25, 'question': 'How long do I have before my unused video session credits expire?', 'answer': '<p>You have to use your video session credits before your primary text subscription expires.</p>\n', 'category_id': 4},
            {'id': 26, 'question': 'How will I know if a new client has been assigned to me?', 'answer': '<p>You will receive a push notification on your app as well as an e-mail notification on your registered email address.</p>\n', 'category_id': 5},
            {'id': 27, 'question': 'How do I know the details of this client and what they are dealing with?', 'answer': '<p>Tap on the name of the client in the top bar in the chat to learn more about the client, what they are dealing with and their subscription plan details.</p>\n', 'category_id': 5},
            {'id': 28, 'question': 'How do I set my availability for video calls on the app?', 'answer': '<p>Go to: Schedule &gt; Manage &gt; Select Date &gt; Select available time slots &gt; Save</p>\n', 'category_id': 5},
            {'id': 29, 'question': 'Can I set my availability for multiple dates at once?', 'answer': '<p>Yes please! We encourage you having your availability set on the app up to 30 days in advance.</p>\n\n<p>Go to: Schedule &gt; Manage &gt; Multi-Select &gt; Select multiple dates &gt; Select available time slots &gt; Save</p>\n', 'category_id': 5},
            {'id': 30, 'question': 'Can the client send me images/video?', 'answer': '<p>No, to protect your privacy we have only enabled the image send option for you. So you can use the image tool to share relevant resources with the client, but they can only share text messages and voice notes with you.</p>\n', 'category_id': 5},
            {'id': 31, 'question': 'How do I report wrongful/indecent behaviour on the client’s part?', 'answer': '<p>Please reach out to <a href="mailto:mhp@spilbloo.com">mhp@spilbloo.com</a> with the subject line &ldquo;Report User: &lt;User Name&gt;&rdquo; and we will respond to that on priority.</p>\n', 'category_id': 5},
            {'id': 32, 'question': 'What do I do if a client is threatening self-harm on the app?', 'answer': '<p>Spilbloo is not an emergency or an SOS therapy platform. Please share the relevant resources such as the Emergency Resources link with them to help guide them in the right direction. Please refer to the Therapist Onboarding Deck for further details.</p>\n', 'category_id': 5},
            {'id': 33, 'question': 'Where can I view my earnings on the app?', 'answer': '<p>You can go to Profile &gt; Earnings to view your lifetime as well monthly breakdown of earnings on Spilbloo.</p>\n', 'category_id': 5},
            {'id': 34, 'question': 'If I need a further breakdown or clarification of my monthly earnings, what do I do?', 'answer': '<p>You can reach out to us at <a href="mailto:mhp@spilbloo.com">mhp@spilbloo.com</a> with your request and we will get back to you with the requested information.</p>\n', 'category_id': 5},
            {'id': 35, 'question': 'Do I need to activate my App Passcode to use the app?', 'answer': '<p>Yes, we require all therapists to have a mandatory App Passcode to add an extra layer of security for the clients&rsquo; confidentiality.</p>\n', 'category_id': 5},
            {'id': 36, 'question': 'Up till when can I reschedule or cancel a video session?', 'answer': '<p>You can reschedule or cancel a video session up to 24 hours prior to the session beginning. We always recommend that you reach out to the client over the chat and inform them before doing so and always provide an alternative time in the event of a cancellation.</p>\n', 'category_id': 5},
            {'id': 37, 'question': 'How do I make edits to my profile or profile picture?', 'answer': '<p>You can reach out to us at <a href="mailto:mhp@spilbloo.com">mhp@spilbloo.com</a> with the requested edits and we can help you with the same.</p>\n', 'category_id': 5},
        ]

        faqs_seeded_count = 0
        for item in faqs_data:
            _, created = Faq.objects.update_or_create(
                id=item['id'],
                defaults={
                    'question': item['question'],
                    'answer': item['answer'],
                    'category_id': item['category_id'],
                    'state_id': Faq.STATE_ACTIVE,
                    'type_id': 0
                }
            )
            if created:
                faqs_seeded_count += 1

        if faqs_seeded_count > 0:
            self.stdout.write(self.style.SUCCESS(f"  + Seeded {faqs_seeded_count} FAQs."))
        else:
            self.stdout.write("  FAQs already seeded and updated.")

        from django.db import connection
        if connection.vendor == 'postgresql':
            with connection.cursor() as cursor:
                cursor.execute("SELECT setval(pg_get_serial_sequence('tbl_category', 'id'), coalesce(max(id), 1)) FROM tbl_category;")
                cursor.execute("SELECT setval(pg_get_serial_sequence('tbl_faq', 'id'), coalesce(max(id), 1)) FROM tbl_faq;")

        self.stdout.write(self.style.SUCCESS("Database seeding completed successfully!"))
