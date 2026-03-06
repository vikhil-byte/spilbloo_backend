from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from faker import Faker
import random
from datetime import datetime, timedelta

User = get_user_model()
fake = Faker()

class Command(BaseCommand):
    help = 'Generate mock users for the admin users table'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=50,
            help='Number of users to create'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing non-superuser users before creating new ones'
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.clear_existing_users()
        
        count = options['count']
        self.stdout.write(f'Creating {count} mock users...')
        
        with transaction.atomic():
            for i in range(count):
                self.create_mock_user(i)
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created {count} users!'))

    def clear_existing_users(self):
        self.stdout.write('Clearing existing non-superuser users...')
        deleted_count = User.objects.filter(is_superuser=False).delete()[0]
        self.stdout.write(f'Deleted {deleted_count} users')

    def create_mock_user(self, index):
        # Generate realistic user data
        first_name = fake.first_name()
        last_name = fake.last_name()
        full_name = f"{first_name} {last_name}"
        email = fake.email()
        
        # Random role distribution
        role_weights = [
            (User.ROLE_USER, 40),      # 40% regular users
            (User.ROLE_PATIENT, 25),   # 25% patients
            (User.ROLE_DOCTER, 20),    # 20% doctors
            (User.ROLE_CLIENT, 10),    # 10% clients
            (User.ROLE_MANAGER, 4),    # 4% managers
            (User.ROLE_ADMIN, 1),      # 1% admin
        ]
        roles, weights = zip(*role_weights)
        role_id = random.choices(roles, weights=weights)[0]
        
        # State distribution (mostly active)
        state_weights = [
            (User.STATE_ACTIVE, 85),   # 85% active
            (User.STATE_INACTIVE, 10), # 10% inactive
            (User.STATE_BANNED, 4),    # 4% banned
            (User.STATE_DELETED, 1),   # 1% deleted
        ]
        states, state_weights = zip(*state_weights)
        state_id = random.choices(states, weights=state_weights)[0]
        
        # Generate date of birth (18-80 years old)
        dob = fake.date_between(start_date='-80y', end_date='-18y')
        
        # Create user
        user = User.objects.create_user(
            email=email,
            password='password123',  # Default password for all mock users
            full_name=full_name,
            date_of_birth=dob,
            gender=random.choice([0, 1, 2]),  # 0=Male, 1=Female, 2=Other
            about_me=fake.text()[:300],
            contact_no=fake.phone_number(),
            address=fake.street_address(),
            latitude=str(fake.latitude()),
            longitude=str(fake.longitude()),
            city=fake.city(),
            country=fake.country(),
            zipcode=fake.postcode(),
            language=random.choice(['en', 'es', 'fr', 'de', 'hi', 'zh']),
            profile_file=f"user_{index+1}.jpg" if random.random() > 0.7 else None,
            tos=1,  # All users have accepted TOS
            role_id=role_id,
            state_id=state_id,
            type_id=random.choice([0, 1]),
            last_visit_time=fake.date_time_between(start_date='-30d', end_date='now'),
            last_action_time=fake.date_time_between(start_date='-7d', end_date='now'),
            last_password_change=fake.date_time_between(start_date='-90d', end_date='-1d'),
            login_error_count=random.randint(0, 3),
            activation_key=None if state_id == User.STATE_ACTIVE else fake.uuid4(),
            timezone=fake.timezone(),
        )
        
        return user
