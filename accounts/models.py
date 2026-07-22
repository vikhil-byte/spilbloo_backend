from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = str(email).strip().lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        # 0 is ROLE_ADMIN
        extra_fields.setdefault('role_id', 0)

        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    # Roles from PHP
    ROLE_ADMIN = 0
    ROLE_MANAGER = 1
    ROLE_USER = 2
    ROLE_CLIENT = 3
    ROLE_PATIENT = 4
    ROLE_DOCTER = 5

    ROLE_CHOICES = (
        (ROLE_ADMIN, 'Admin'),
        (ROLE_MANAGER, 'Manager'),
        (ROLE_USER, 'User'),
        (ROLE_CLIENT, 'Client'),
        (ROLE_PATIENT, 'Patient'),
        (ROLE_DOCTER, 'Doctor'),
    )

    # State from PHP
    STATE_INACTIVE = 0
    STATE_ACTIVE = 1
    STATE_BANNED = 2
    STATE_DELETED = 3

    STATE_CHOICES = (
        (STATE_INACTIVE, 'Inactive'),
        (STATE_ACTIVE, 'Active'),
        (STATE_BANNED, 'Banned'),
        (STATE_DELETED, 'Deleted'),
    )

    # Let's remove username and use email as the primary identifying field
    username = None
    email = models.EmailField(unique=True)

    # Fields mapped from PHP
    full_name = models.CharField(max_length=255, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.SmallIntegerField(blank=True, null=True)
    about_me = models.TextField(blank=True, null=True)
    contact_no = models.CharField(max_length=50, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    latitude = models.CharField(max_length=50, blank=True, null=True)
    longitude = models.CharField(max_length=50, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    zipcode = models.CharField(max_length=20, blank=True, null=True)
    language = models.CharField(max_length=50, blank=True, null=True)
    profile_file = models.CharField(max_length=255, blank=True, null=True)
    tos = models.SmallIntegerField(default=0)
    
    role_id = models.SmallIntegerField(choices=ROLE_CHOICES, default=ROLE_USER)
    state_id = models.SmallIntegerField(choices=STATE_CHOICES, default=STATE_ACTIVE)
    type_id = models.SmallIntegerField(default=0)

    qualification = models.CharField(max_length=255, blank=True, null=True)
    experience = models.IntegerField(default=0, blank=True, null=True)
    sessions_completed = models.IntegerField(default=0, blank=True, null=True)
    online = models.CharField(max_length=50, default='no', blank=True, null=True)
    is_available = models.BooleanField(default=True)
    token = models.CharField(max_length=255, default='', blank=True, null=True)

    therapist_gender = models.IntegerField(default=0, blank=True, null=True)
    doctor_id = models.IntegerField(blank=True, null=True)
    doctor_assigned_time = models.DateTimeField(blank=True, null=True)
    video_credit = models.CharField(max_length=16, default='0', blank=True, null=True)
    age_group = models.CharField(max_length=16, blank=True, null=True)
    designation = models.IntegerField(blank=True, null=True)
    push_enabled = models.SmallIntegerField(default=1, blank=True, null=True)
    email_enabled = models.SmallIntegerField(default=1, blank=True, null=True)
    consent_accepted_on = models.DateTimeField(blank=True, null=True)
    is_consent_accept = models.IntegerField(default=0, blank=True, null=True)
    otp = models.IntegerField(blank=True, null=True)
    otp_verified = models.IntegerField(default=0, blank=True, null=True)
    email_verified = models.SmallIntegerField(default=0, blank=True, null=True)

    last_visit_time = models.DateTimeField(blank=True, null=True)
    last_action_time = models.DateTimeField(blank=True, null=True)
    last_password_change = models.DateTimeField(blank=True, null=True)
    login_error_count = models.IntegerField(default=0)
    activation_key = models.CharField(max_length=255, blank=True, null=True)
    timezone = models.CharField(max_length=100, blank=True, null=True)

    # Track usage (matches created_on/updated_on from PHP)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    created_by_id = models.IntegerField(blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']

    objects = UserManager()

    class Meta:
        db_table = 'tbl_user'

    def __str__(self):
        return self.full_name or self.email

    def save(self, *args, **kwargs):
        # Normalize/sync name fields
        if self.full_name:
            self.full_name = self.full_name.strip()
            if not self.first_name and not self.last_name:
                parts = self.full_name.split(' ', 1)
                self.first_name = parts[0]
                self.last_name = parts[1] if len(parts) > 1 else ''
        elif self.first_name or self.last_name:
            self.full_name = f"{self.first_name or ''} {self.last_name or ''}".strip()
        super().save(*args, **kwargs)



    def get_affirmation_for_the_day(self):
        affirmations = [
            "I prioritize self-care and nurture my mental well-being.",
            "I release stress and anxiety, replacing them with inner peace.",
            "I am in control of my thoughts and choose positivity.",
            "I practice mindfulness and stay present in the moment.",
            "I embrace my emotions and allow myself to feel.",
            "I am resilient and can overcome any challenges.",
            "I am worthy of love, compassion, and self-acceptance.",
            "I seek help and support when needed, knowing it's a sign of strength.",
            "I let go of past burdens and forgive myself.",
            "I trust in the journey of healing and growth."
        ]
        import datetime
        day_of_year = datetime.datetime.now().timetuple().tm_yday
        selected_index = day_of_year % len(affirmations)
        return affirmations[selected_index]

class HaLogins(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ha_logins', db_column='user_id_fk', blank=True, null=True) 
    # Use a different db_column for the ForeignKey if we are keeping user_id_str as user_id.
    user_id_str = models.CharField(max_length=50, db_column='user_id')
    login_provider = models.CharField(max_length=50)
    login_provider_identifier = models.CharField(max_length=100)
    
    # Tracking fields
    created_by_id = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = 'ha_logins'

    def __str__(self):
        return self.user_id_str
