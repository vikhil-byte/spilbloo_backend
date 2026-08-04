"""
Create demo accounts for App Store / Play Store review.

These accounts let Apple/Google reviewers log in to a pre-populated app
without you handing over a real user's credentials.

Usage:
    python manage.py setup_review_accounts            # create + activate
    python manage.py setup_review_accounts --deactivate  # disable after approval
    python manage.py setup_review_accounts --status      # check current state

Workflow:
    1. Run this command (creates user + therapist + seed data, activates them).
    2. Put the credentials below into App Store Connect "Review Notes"
       and Google Play Console "Login credentials".
    3. Submit the build for review.
    4. After approval, run with --deactivate so the accounts stop working.

Security notes:
    - Credentials are NOT hardcoded in the app source code.
    - They live only in the database, toggleable via Django admin / this command.
    - The password is intentionally strong; store it in a password manager.
    - Set is_active=False after each review to prevent abuse.
"""
import secrets
import string

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from accounts.models import User
from core.models import (
    NodeSubscriptionPlan,
    NodeUserSelectedTherapistPlan,
    TherapistEarning,
    ChatsHistory,
)

# ----------------------------------------------------------------------------
# Demo credentials — these are what you paste into App Store / Play review
# fields. Override via env vars if you want different values per environment.
#
# IMPORTANT — login methods differ by role:
#   - USER app:      OTP-based login. Reviewer enters the email, receives/guesses
#                    OTP. On staging/dev (ENVIRONMENT != production) the magic
#                    OTP "1234" always works for ANY account (see VerifyOtpView).
#                    So the demo USER needs NO password — only the email + "1234".
#   - THERAPIST app: email + password login (LoginForm flow). The demo therapist
#                    needs a real password, set below and toggleable via is_active.
# ----------------------------------------------------------------------------
import os

DEFAULT_USER_EMAIL = os.environ.get(
    'REVIEW_USER_EMAIL', 'user@spilbloo.com'
)
DEFAULT_THERAPIST_EMAIL = os.environ.get(
    'REVIEW_THERAPIST_EMAIL', 'therapist@spilbloo.com'
)
DEFAULT_THERAPIST_PASSWORD = os.environ.get(
    'REVIEW_THERAPIST_PASSWORD', 'demo1234'
)
# Magic OTP that works on staging/dev for any user account.
MAGIC_STAGING_OTP = os.environ.get('REVIEW_USER_OTP', '1234')


class Command(BaseCommand):
    help = 'Create or toggle demo accounts for App Store / Play Store review.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--deactivate',
            action='store_true',
            help='Disable the demo accounts (run after a review is approved).',
        )
        parser.add_argument(
            '--status',
            action='store_true',
            help='Print the current state of the demo accounts and exit.',
        )
        parser.add_argument(
            '--therapist-password',
            default=DEFAULT_THERAPIST_PASSWORD,
            help='Password for the demo THERAPIST account (user account uses OTP, no password).',
        )

    def handle(self, *args, **options):
        emails = [DEFAULT_USER_EMAIL, DEFAULT_THERAPIST_EMAIL]

        if options['status']:
            return self._print_status(emails)

        if options['deactivate']:
            return self._toggle(emails, active=False)

        therapist_password = options['therapist_password']
        # User account: OTP-based, no password. OTP "1234" works on staging.
        self._create_user(DEFAULT_USER_EMAIL)
        therapist = self._create_therapist(DEFAULT_THERAPIST_EMAIL, therapist_password)
        self._link_user_to_therapist(DEFAULT_USER_EMAIL, therapist)
        self._seed_earnings(DEFAULT_USER_EMAIL, therapist)
        self._seed_chat(DEFAULT_USER_EMAIL, therapist)

        is_staging = os.environ.get('ENVIRONMENT', 'staging').lower() in (
            'staging', 'dev', 'development'
        )
        # On production, a per-email magic OTP can be enabled via .env so the
        # reviewer can log in without access to the real emailed OTP.
        prod_review_otp_configured = bool(
            os.environ.get('REVIEW_OTP_EMAIL', '').strip()
        ) and bool(os.environ.get('REVIEW_OTP', '').strip())

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✓ Review accounts ready and ACTIVE.'))
        self.stdout.write(self.style.WARNING(
            'Paste these into App Store Connect (Review Notes) and '
            'Google Play Console (Login credentials):'
        ))
        self.stdout.write('')
        self.stdout.write('  USER APP (OTP login):')
        self.stdout.write(f'    Email:  {DEFAULT_USER_EMAIL}')
        if is_staging:
            self.stdout.write(f'    OTP:    {MAGIC_STAGING_OTP}  '
                              '(magic OTP works on staging/dev for any account)')
        elif prod_review_otp_configured:
            self.stdout.write(f'    OTP:    {os.environ.get("REVIEW_OTP")}  '
                              '(per-email magic OTP from .env — works for this email only)')
        else:
            self.stdout.write(self.style.ERROR(
                '    OTP:    ⚠ PRODUCTION with no REVIEW_OTP_* in .env'
            ))
            self.stdout.write(self.style.WARNING(
                '           Set REVIEW_OTP_EMAIL + REVIEW_OTP in .env so the reviewer '
                'can log in. Real OTP is emailed to an address they cannot access.'
            ))
        self.stdout.write('')
        self.stdout.write('  THERAPIST APP (email + password login):')
        self.stdout.write(f'    Email:     {DEFAULT_THERAPIST_EMAIL}')
        self.stdout.write(f'    Password:  {therapist_password}')
        self.stdout.write('')
        self.stdout.write(self.style.WARNING(
            'After approval:  (1) run setup_review_accounts --deactivate,  '
            '(2) blank REVIEW_OTP_* in .env on prod, (3) restart the app.'
        ))

    # ------------------------------------------------------------------ create

    def _create_user(self, email):
        """Create the demo USER account. Login is OTP-based — no password set.
        On staging/dev the magic OTP (default '1234') verifies any account.
        Uses ROLE_PATIENT (4) because that's the role_id the iOS/Android user
        app sends on login (SelectRole.pateint = 4)."""
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'full_name': 'Demo Reviewer',
                'role_id': User.ROLE_PATIENT,
                'state_id': User.STATE_ACTIVE,
                'is_active': True,
                'city': 'Mumbai',
                'country': 'India',
                'gender': 1,
                'email_verified': 1,
                'is_consent_accept': 1,
                'consent_accepted_on': timezone.now(),
                'otp_verified': 1,
            },
        )
        if not created:
            # Existing account — reactivate AND fix role_id in case it was created
            # with the wrong role (e.g. ROLE_USER=2 instead of ROLE_PATIENT=4).
            changed = []
            if user.is_active is not True:
                user.is_active = True
                changed.append('is_active')
            if user.state_id != User.STATE_ACTIVE:
                user.state_id = User.STATE_ACTIVE
                changed.append('state_id')
            if user.role_id != User.ROLE_PATIENT:
                user.role_id = User.ROLE_PATIENT
                changed.append(f'role_id→{User.ROLE_PATIENT} (patient)')
            if changed:
                user.save()
                self.stdout.write(f'  ↻ Reactivated + fixed {email} ({", ".join(changed)})')
            else:
                self.stdout.write(f'  ↻ Already correct: {email}')
        else:
            # OTP users get an unusable password so password login can never succeed.
            user.set_unusable_password()
            user.save()
            self.stdout.write(f'  + Created user (OTP login): {email}')
        return user

    def _create_therapist(self, email, password):
        """Create the demo THERAPIST account. Login is email + password.
        Marked is_hidden_from_directory=True so it never appears in patient-facing
        therapist lists, while remaining loginable for the therapist-app review."""
        t, created = User.objects.get_or_create(
            email=email,
            defaults={
                'full_name': 'Dr. Review Therapist',
                'role_id': User.ROLE_DOCTER,
                'state_id': User.STATE_ACTIVE,
                'is_active': True,
                'is_hidden_from_directory': True,
                'qualification': 'M.A. Counseling Psychology',
                'experience': 7,
                'sessions_completed': 120,
                'about_me': (
                    'Demo therapist account for store review. Compassionate, '
                    'evidence-based practitioner specialised in anxiety, '
                    'depression, and relationship counselling.'
                ),
                'language': 'English, Hindi',
                'city': 'Bengaluru',
                'country': 'India',
                'online': 'yes',
                'is_available': True,
                'email_verified': 1,
                'otp_verified': 1,
            },
        )
        if not created:
            t.is_active = True
            t.state_id = User.STATE_ACTIVE
            t.is_hidden_from_directory = True
            t.set_password(password)
            t.save()
            self.stdout.write(f'  ↻ Reactivated existing therapist (hidden from directory): {email}')
        else:
            t.set_password(password)
            t.save()
            self.stdout.write(f'  + Created therapist (password login, hidden from directory): {email}')
        return t

    # ------------------------------------------------------------------ seed

    def _link_user_to_therapist(self, user_email, therapist):
        """Attach an active subscription plan so the user has a paid session."""
        user = User.objects.get(email=user_email)
        plan = NodeSubscriptionPlan.objects.first()
        if not plan:
            self.stdout.write(self.style.WARNING(
                '  ! No NodeSubscriptionPlan rows found — skipping plan link. '
                'Create a plan in admin first, then re-run.'
            ))
            return
        NodeUserSelectedTherapistPlan.objects.update_or_create(
            user_id=user.id,
            therapist_id=therapist.id,
            defaults={
                'plan_id': plan.id,
                'selected_on': timezone.now(),
            },
        )
        self.stdout.write(
            f'  + Linked user → therapist (plan: {plan.plan_name})'
        )

    def _seed_earnings(self, user_email, therapist):
        """Give the therapist a sample earning entry so the dashboard isn't empty."""
        user = User.objects.get(email=user_email)
        TherapistEarning.objects.get_or_create(
            therapist=therapist,
            patient=user,
            type_id=TherapistEarning.TYPE_SUBSCRIPTION_PLAN,
            defaults={
                'date': timezone.now(),
                'amount': '1500.00',
                'mimblu_earning': '300.00',
                'completed_booking': 1,
                'state_id': TherapistEarning.STATE_ACTIVE,
                'created_by': therapist,
            },
        )
        self.stdout.write('  + Seeded one therapist earning record')

    def _seed_chat(self, user_email, therapist):
        """One sample chat message so the chat screen shows content."""
        user = User.objects.get(email=user_email)
        ChatsHistory.objects.get_or_create(
            user_id=user.id,
            chats_message='Hi Dr. Review Therapist, I would like to book a session.',
        )
        ChatsHistory.objects.get_or_create(
            user_id=therapist.id,
            chats_message='Hello! Welcome to Spilbloo. I have slots available this week.',
        )
        self.stdout.write('  + Seeded sample chat messages')

    # ------------------------------------------------------------------ utils

    def _toggle(self, emails, active):
        verb = 'Activated' if active else 'Deactivated'
        for email in emails:
            try:
                u = User.objects.get(email=email)
            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f'  ! {email} does not exist — run without flags to create it first.'
                ))
                continue
            u.is_active = active
            u.save()
            self.stdout.write(self.style.SUCCESS(f'  {verb}: {email}'))
        action = 'activated for review' if active else 'DEACTIVATED (safe)'
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'✓ Review accounts {action}.'))

    def _print_status(self, emails):
        self.stdout.write('Review account status:')
        for email in emails:
            try:
                u = User.objects.get(email=email)
                role = u.get_role_id_display()
                state = 'ACTIVE' if u.is_active else 'inactive'
                self.stdout.write(f'  {email}  →  {role}, {state}')
            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f'  {email}  →  NOT CREATED (run setup to create)'
                ))
