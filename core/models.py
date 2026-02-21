from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL

class TherapistEarning(models.Model):
    # States
    STATE_INACTIVE = 0
    STATE_ACTIVE = 1
    STATE_DELETED = 2

    STATE_CHOICES = (
        (STATE_INACTIVE, 'New'),
        (STATE_ACTIVE, 'Active'),
        (STATE_DELETED, 'Deleted'),
    )

    # Types
    TYPE_SUBSCRIPTION_PLAN = 1
    TYPE_VIDEO_PLAN = 2

    TYPE_CHOICES = (
        (TYPE_SUBSCRIPTION_PLAN, 'Subscription Plan'),
        (TYPE_VIDEO_PLAN, 'Video Plan')
    )

    therapist = models.ForeignKey(User, on_delete=models.CASCADE, related_name='therapist_earnings')
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='patient_earnings')
    date = models.DateTimeField()
    amount = models.CharField(max_length=16, blank=True, null=True)
    mimblu_earning = models.CharField(max_length=16, blank=True, null=True)
    completed_booking = models.IntegerField(default=0)
    
    state_id = models.SmallIntegerField(choices=STATE_CHOICES, default=STATE_ACTIVE)
    type_id = models.SmallIntegerField(choices=TYPE_CHOICES, default=0)

    # Tracking fields
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_earnings')

    class Meta:
        db_table = 'tbl_therapist_earning'

    def __str__(self):
        return f"Earning {self.id} - Therapist {self.therapist_id}"

class ContactForm(models.Model):
    # States
    STATE_INACTIVE = 0
    STATE_ACCEPT = 1
    STATE_REJECT = 2
    STATE_ADD = 3

    STATE_CHOICES = (
        (STATE_INACTIVE, 'New'),
        (STATE_ACCEPT, 'Accept'),
        (STATE_REJECT, 'Reject'),
        (STATE_ADD, 'Added'),
    )

    name = models.CharField(max_length=256)
    email = models.EmailField(max_length=255)
    contact_no = models.CharField(max_length=32, blank=True, null=True)
    city = models.CharField(max_length=128, blank=True, null=True)
    country_code = models.CharField(max_length=16, blank=True, null=True)
    experience = models.CharField(max_length=16, blank=True, null=True)
    
    state_id = models.SmallIntegerField(choices=STATE_CHOICES, default=STATE_ACCEPT)
    type_id = models.SmallIntegerField(default=0)

    # Tracking fields
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_contact_forms')

    class Meta:
        db_table = 'tbl_contact_form'

    def __str__(self):
        return self.name

class DoctorReason(models.Model):
    # States
    STATE_INACTIVE = 0
    STATE_ACTIVE = 1
    STATE_DELETED = 2

    STATE_CHOICES = (
        (STATE_INACTIVE, 'New'),
        (STATE_ACTIVE, 'Active'),
        (STATE_DELETED, 'Deleted'),
    )

    title = models.CharField(max_length=256)
    
    state_id = models.SmallIntegerField(choices=STATE_CHOICES, default=STATE_ACTIVE)
    type_id = models.SmallIntegerField(default=0)

    # Tracking fields
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_doctor_reasons')

    class Meta:
        db_table = 'tbl_doctor_reason'

    def __str__(self):
        return self.title

class Symptom(models.Model):
    # States
    STATE_INACTIVE = 0
    STATE_ACTIVE = 1
    STATE_DELETED = 2

    STATE_CHOICES = (
        (STATE_INACTIVE, 'New'),
        (STATE_ACTIVE, 'Active'),
        (STATE_DELETED, 'Deleted'),
    )

    title = models.CharField(max_length=255, unique=True)
    
    state_id = models.SmallIntegerField(choices=STATE_CHOICES, default=STATE_ACTIVE)
    type_id = models.SmallIntegerField(default=0)

    # Tracking fields
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_symptoms')

    class Meta:
        db_table = 'tbl_symptom'

    def __str__(self):
        return self.title

class DoctorRequest(models.Model):
    # States
    STATE_INACTIVE = 0
    STATE_ACTIVE = 1
    STATE_DELETED = 2

    STATE_CHOICES = (
        (STATE_INACTIVE, 'New'),
        (STATE_ACTIVE, 'Active'),
        (STATE_DELETED, 'Deleted'),
    )

    description = models.TextField(blank=True, null=True)
    reason = models.ForeignKey(DoctorReason, on_delete=models.CASCADE, related_name='doctor_requests')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_doctor_requests')
    
    state_id = models.SmallIntegerField(choices=STATE_CHOICES, default=STATE_ACTIVE)
    type_id = models.SmallIntegerField(default=0)

    # Tracking fields
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_doctor_requests')

    class Meta:
        db_table = 'tbl_doctor_request'

    def __str__(self):
        return f"Request {self.id} for Doctor {self.doctor_id}"

class Feed(models.Model):
    # States
    STATE_INACTIVE = 0
    STATE_ACTIVE = 1
    STATE_DELETED = 2

    STATE_CHOICES = (
        (STATE_INACTIVE, 'New'),
        (STATE_ACTIVE, 'Active'),
        (STATE_DELETED, 'Deleted'),
    )

    content = models.TextField(blank=True, null=True)
    
    state_id = models.SmallIntegerField(choices=STATE_CHOICES, default=STATE_ACTIVE)
    type_id = models.SmallIntegerField(default=0)
    
    model_type = models.CharField(max_length=128)
    model_id = models.IntegerField()
    user_ip = models.CharField(max_length=255, blank=True, null=True)
    user_agent = models.CharField(max_length=255, blank=True, null=True)

    # Tracking fields
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='user_feeds')

    class Meta:
        db_table = 'tbl_feed'

    def __str__(self):
        return f"Feed {self.id} - {self.model_type}"

class EmergencyResource(models.Model):
    # States
    STATE_INACTIVE = 0
    STATE_ACTIVE = 1
    STATE_DELETED = 2

    STATE_CHOICES = (
        (STATE_INACTIVE, 'New'),
        (STATE_ACTIVE, 'Active'),
        (STATE_DELETED, 'Deleted'),
    )

    title = models.CharField(max_length=256, unique=True)
    contact_no = models.CharField(max_length=32)
    alternate_contact_no = models.CharField(max_length=32, blank=True, null=True)
    link = models.CharField(max_length=255, blank=True, null=True)
    timings = models.CharField(max_length=128, blank=True, null=True)
    
    state_id = models.SmallIntegerField(choices=STATE_CHOICES, default=STATE_ACTIVE)
    type_id = models.SmallIntegerField(default=0)

    # Tracking fields
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_emergency_resources')

    class Meta:
        db_table = 'tbl_emergency_resource'

    def __str__(self):
        return self.title

class AgeGroup(models.Model):
    # States
    STATE_INACTIVE = 0
    STATE_ACTIVE = 1
    STATE_DELETED = 2

    STATE_CHOICES = (
        (STATE_INACTIVE, 'New'),
        (STATE_ACTIVE, 'Active'),
        (STATE_DELETED, 'Deleted'),
    )

    title = models.CharField(max_length=256)
    group_id = models.IntegerField()
    
    state_id = models.SmallIntegerField(choices=STATE_CHOICES, default=STATE_ACTIVE)
    type_id = models.SmallIntegerField(default=0)

    # Tracking fields
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_age_groups')

    class Meta:
        db_table = 'tbl_age_group'

    def __str__(self):
        return self.title

class AssignedTherapist(models.Model):
    # States
    STATE_ASSIGNED = 1
    STATE_CHANGED = 2

    STATE_CHOICES = (
        (STATE_ASSIGNED, 'Assigned'),
        (STATE_CHANGED, 'Changed'),
    )

    therapist = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_therapist_records')
    therapist_email = models.EmailField(max_length=255, blank=True, null=True)
    therapist_name = models.CharField(max_length=128, blank=True, null=True)
    
    assigned_on = models.DateTimeField()
    changed_on = models.DateTimeField(blank=True, null=True)
    
    state_id = models.SmallIntegerField(choices=STATE_CHOICES, default=STATE_ASSIGNED)
    type_id = models.SmallIntegerField(default=0)

    # Tracking fields
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assigned_therapists_created')

    class Meta:
        db_table = 'tbl_assigned_therapist'

    def __str__(self):
        return f"Therapist {self.therapist_id} assigned by {self.created_by_id}"

class BestDoctor(models.Model):
    # States
    STATE_INACTIVE = 0
    STATE_ACTIVE = 1
    STATE_DELETED = 2

    STATE_CHOICES = (
        (STATE_INACTIVE, 'New'),
        (STATE_ACTIVE, 'Active'),
        (STATE_DELETED, 'Deleted'),
    )

    title = models.CharField(max_length=128)
    name = models.CharField(max_length=128)
    discription = models.TextField(blank=True, null=True) # Keeping typo from PHP or fix to description? Keeping for DB match
    image_file = models.CharField(max_length=255, blank=True, null=True)
    speciality = models.CharField(max_length=255, blank=True, null=True) # Stored as string ID or name in PHP? (PHP rules say safe/trim, max length implied by DB. In BestDoctor::getSpecialityName it looks up Symptom ID. We'll store as string and maybe relate later if needed, PHP stores it as a safe field)
    
    state_id = models.SmallIntegerField(choices=STATE_CHOICES, default=STATE_ACTIVE)
    type_id = models.SmallIntegerField(default=0)

    # Tracking fields
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_best_doctors')

    class Meta:
        db_table = 'tbl_best_doctor'

    def __str__(self):
        return self.name

class VideoPlan(models.Model):
    # States
    STATE_INACTIVE = 0
    STATE_ACTIVE = 1
    STATE_DELETED = 2

    STATE_CHOICES = (
        (STATE_INACTIVE, 'New'),
        (STATE_ACTIVE, 'Active'),
        (STATE_DELETED, 'Deleted'),
    )

    IS_RECOMMENDED_NO = 0
    IS_RECOMMENDED_YES = 1

    RECOMMENDED_CHOICES = (
        (IS_RECOMMENDED_NO, 'No'),
        (IS_RECOMMENDED_YES, 'Yes'),
    )

    title = models.CharField(max_length=128)
    image_file = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    video_description = models.TextField(blank=True, null=True)
    
    currency_code = models.CharField(max_length=16, blank=True, null=True)
    discounted_price = models.CharField(max_length=16)
    total_price = models.CharField(max_length=16)
    tax_price = models.CharField(max_length=16, blank=True, null=True) # Usually DecimalField, keeping as Char string or Decimal in Dj? Let's use Decimal for Django if possible, but matching CharField sizes. We'll use DecimalField for all price to be safe, even if PHP has varchar. Wait, length 16. DecimalField is better.
    tax_percentage = models.CharField(max_length=16, blank=True, null=True)
    final_price = models.CharField(max_length=16, blank=True, null=True)
    doctor_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    gross_price_per_video = models.CharField(max_length=16)
    net_price_per_video = models.CharField(max_length=16)

    credit = models.IntegerField()
    is_recommended = models.SmallIntegerField(choices=RECOMMENDED_CHOICES, default=IS_RECOMMENDED_NO)
    
    state_id = models.SmallIntegerField(choices=STATE_CHOICES, default=STATE_ACTIVE)
    type_id = models.SmallIntegerField(default=0)

    # Tracking fields
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_video_plans')

    class Meta:
        db_table = 'tbl_video_plan'

    def __str__(self):
        return self.title

class VideoCoupon(models.Model):
    # Types
    TYPE_FLAT = 1
    TYPE_PERCENTAGE = 2
    
    TYPE_CHOICES = (
        (TYPE_FLAT, 'Flat'),
        (TYPE_PERCENTAGE, 'Percentage'),
    )

    # States
    STATE_INACTIVE = 0
    STATE_ACTIVE = 1
    STATE_DELETED = 2

    STATE_CHOICES = (
        (STATE_INACTIVE, 'New'),
        (STATE_ACTIVE, 'Active'),
        (STATE_DELETED, 'Deleted'),
    )

    code = models.CharField(max_length=255, unique=True)
    amount = models.CharField(max_length=16)
    plan_id = models.CharField(max_length=255, blank=True, null=True) # PHP stores plan IDs as comma-separated string
    min_amount = models.CharField(max_length=16, blank=True, null=True)
    
    description = models.TextField(blank=True, null=True)
    valid_till = models.DateTimeField(blank=True, null=True)
    
    limit = models.IntegerField(default=1)
    user_limit = models.IntegerField(default=1)

    type_id = models.SmallIntegerField(choices=TYPE_CHOICES, default=TYPE_FLAT)
    state_id = models.SmallIntegerField(choices=STATE_CHOICES, default=STATE_ACTIVE)

    # Tracking fields
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_video_coupons')

    class Meta:
        db_table = 'tbl_video_coupon'

    def __str__(self):
        return self.code

class CouponUser(models.Model):
    # States
    STATE_INACTIVE = 0
    STATE_ACTIVE = 1
    STATE_DELETED = 2

    STATE_CHOICES = (
        (STATE_INACTIVE, 'New'),
        (STATE_ACTIVE, 'Active'),
        (STATE_DELETED, 'Deleted'),
    )

    coupon = models.ForeignKey(VideoCoupon, on_delete=models.CASCADE, related_name='coupon_users')
    plan = models.ForeignKey(VideoPlan, on_delete=models.CASCADE, related_name='plan_coupon_uses')
    # subscribed_video = models.ForeignKey('SubscribedVideo', on_delete=models.CASCADE, related_name='coupon_uses') # Wait, circular ref or just string. We will string it.
    subscribed_video_id = models.IntegerField()
    coupon_code = models.CharField(max_length=255)
    
    state_id = models.SmallIntegerField(choices=STATE_CHOICES, default=STATE_ACTIVE)
    type_id = models.SmallIntegerField(default=0)

    # Tracking fields
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='used_coupons')

    class Meta:
        db_table = 'tbl_coupon_user'

    def __str__(self):
        return f"Coupon {self.coupon_id} used by {self.created_by_id}"

class SubscribedVideo(models.Model):
    # States
    STATE_INACTIVE = 0
    STATE_ACTIVE = 1
    STATE_DELETED = 2

    STATE_CHOICES = (
        (STATE_INACTIVE, 'New'),
        (STATE_ACTIVE, 'Active'),
        (STATE_DELETED, 'Deleted'),
    )

    TYPE_COUPON_APPLIED = 1
    TYPE_COUPON_NOT_APPLIED = 2

    TYPE_CHOICES = (
        (TYPE_COUPON_APPLIED, 'Yes'),
        (TYPE_COUPON_NOT_APPLIED, 'No'),
    )

    plan = models.ForeignKey(VideoPlan, on_delete=models.CASCADE, related_name='subscribed_videos')
    transaction_id = models.CharField(max_length=32, blank=True, null=True)
    
    doctor_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    coupon = models.CharField(max_length=255, blank=True, null=True)
    coupon_discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    plan_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    gst_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    final_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    address = models.TextField(blank=True, null=True)
    country = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=255, blank=True, null=True)
    contact = models.CharField(max_length=255, blank=True, null=True)

    state_id = models.SmallIntegerField(choices=STATE_CHOICES, default=STATE_ACTIVE)
    type_id = models.SmallIntegerField(choices=TYPE_CHOICES, default=TYPE_COUPON_NOT_APPLIED)

    # Tracking fields
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='video_subscriptions')

    class Meta:
        db_table = 'tbl_subscribed_video'

    def __str__(self):
        return f"Subscription {self.id} for Plan {self.plan_id}"

class UserSymptom(models.Model):
    # States
    STATE_INACTIVE = 0
    STATE_ACTIVE = 1
    STATE_DELETED = 2

    STATE_CHOICES = (
        (STATE_INACTIVE, 'New'),
        (STATE_ACTIVE, 'Active'),
        (STATE_DELETED, 'Deleted'),
    )

    title = models.CharField(max_length=256, blank=True, null=True)
    symptom = models.ForeignKey(Symptom, on_delete=models.CASCADE, related_name='user_symptoms')
    
    state_id = models.SmallIntegerField(choices=STATE_CHOICES, default=STATE_ACTIVE)
    type_id = models.SmallIntegerField(default=0)

    # Tracking fields
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='my_symptoms')

    class Meta:
        db_table = 'tbl_user_symptom'

    def __str__(self):
        return f"Symptom {self.symptom_id} for User {self.created_by_id}"

class Setting(models.Model):
    # Types
    KEY_TYPE_STRING = 0
    KEY_TYPE_BOOL = 1
    KEY_TYPE_INT = 2
    KEY_TYPE_EMAIL = 3
    KEY_TYPE_TIME = 4
    KEY_TYPE_DATE = 5
    KEY_TYPE_TEXT = 6

    TYPE_CHOICES = (
        (KEY_TYPE_STRING, 'String'),
        (KEY_TYPE_BOOL, 'Boolean'),
        (KEY_TYPE_INT, 'Integer'),
        (KEY_TYPE_EMAIL, 'Email'),
        (KEY_TYPE_TIME, 'Time'),
        (KEY_TYPE_DATE, 'Date'),
        (KEY_TYPE_TEXT, 'Text'),
    )

    # States
    STATE_INACTIVE = 0
    STATE_ACTIVE = 1
    STATE_DELETED = 2

    STATE_CHOICES = (
        (STATE_INACTIVE, 'New'),
        (STATE_ACTIVE, 'Active'),
        (STATE_DELETED, 'Archived'),
    )

    key = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    value = models.TextField(blank=True, null=True)
    
    type_id = models.SmallIntegerField(choices=TYPE_CHOICES, default=KEY_TYPE_STRING)
    state_id = models.SmallIntegerField(choices=STATE_CHOICES, default=STATE_ACTIVE)

    # Tracking fields
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='settings_created') # In PHP no created_on field in table structure definition for Setting? Checking lines 14-22. I'll omit created_on but keep created_by.

    class Meta:
        db_table = 'tbl_setting'

    def __str__(self):
        return self.title

class Disclaimer(models.Model):
    # States
    STATE_INACTIVE = 0
    STATE_ACTIVE = 1
    STATE_DELETED = 2

    STATE_CHOICES = (
        (STATE_INACTIVE, 'New'),
        (STATE_ACTIVE, 'Active'),
        (STATE_DELETED, 'Deleted'),
    )

    title = models.CharField(max_length=128)
    discription = models.TextField(blank=True, null=True) # retaining typo
    
    state_id = models.SmallIntegerField(choices=STATE_CHOICES, default=STATE_ACTIVE)
    type_id = models.SmallIntegerField(default=0)

    # Tracking fields
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_disclaimers')

    class Meta:
        db_table = 'tbl_disclaimer'

    def __str__(self):
        return self.title

class PushNotification(models.Model):
    # States
    STATE_INACTIVE = 0
    STATE_PENDING = 1
    STATE_SENT = 2
    STATE_FAILED = 3

    STATE_CHOICES = (
        (STATE_INACTIVE, 'New'),
        (STATE_PENDING, 'Pending'),
        (STATE_SENT, 'Sent'),
        (STATE_FAILED, 'Failed'),
    )

    # User Types
    TYPE_SUBSCRIBED_USER = 1
    TYPE_UNSUBSCRIBED_USER = 2
    TYPE_EXPIRED_SUBSCRIPTION_USER = 3
    TYPE_THERAPIST = 4
    TYPE_COMMON = 5

    TYPE_CHOICES = (
        (TYPE_SUBSCRIBED_USER, 'Subscribed Users'),
        (TYPE_UNSUBSCRIBED_USER, 'Not Subscribed Users'),
        (TYPE_EXPIRED_SUBSCRIPTION_USER, 'Expired Subscription Users'),
        (TYPE_THERAPIST, 'Therapist'),
        (TYPE_COMMON, 'Everyone'),
    )

    # Role Types
    ROLE_TYPE_USER = 1
    ROLE_TYPE_THERAPIST = 2
    ROLE_TYPE_BOTH = 3

    ROLE_TYPE_CHOICES = (
        (ROLE_TYPE_USER, 'User'),
        (ROLE_TYPE_THERAPIST, 'Therapist'),
        (ROLE_TYPE_BOTH, 'Both'),
    )

    title = models.CharField(max_length=256)
    description = models.TextField()
    role_type = models.SmallIntegerField(choices=ROLE_TYPE_CHOICES)
    
    state_id = models.SmallIntegerField(choices=STATE_CHOICES, default=STATE_INACTIVE)
    type_id = models.SmallIntegerField(choices=TYPE_CHOICES, blank=True, null=True)

    # Tracking fields
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_push_notifications')

    class Meta:
        db_table = 'tbl_push_notification'

    def __str__(self):
        return self.title

class File(models.Model):
    # Types
    TYPE_FILE = 0
    TYPE_LINK = 1
    TYPE_URL = 2

    TYPE_CHOICES = (
        (TYPE_FILE, 'File'),
        (TYPE_LINK, 'SymbolicLink'),
        (TYPE_URL, 'URL'),
    )

    name = models.CharField(max_length=1024)
    size = models.IntegerField(default=0)
    key = models.CharField(max_length=255)
    model_type = models.CharField(max_length=128)
    model_id = models.IntegerField(blank=True, null=True)
    
    type_id = models.SmallIntegerField(choices=TYPE_CHOICES, default=TYPE_FILE)

    # Tracking fields
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='uploaded_files')

    class Meta:
        db_table = 'tbl_file'

    def __str__(self):
        return self.name

class Currency(models.Model):
    # States
    STATE_INACTIVE = 0
    STATE_ACTIVE = 1
    STATE_DELETED = 2

    STATE_CHOICES = (
        (STATE_INACTIVE, 'New'),
        (STATE_ACTIVE, 'Active'),
        (STATE_DELETED, 'Deleted'),
    )

    country = models.CharField(max_length=255)
    code = models.CharField(max_length=255)
    symbol = models.CharField(max_length=255)
    conversion_rate = models.FloatField(default=1.0)
    
    state_id = models.SmallIntegerField(choices=STATE_CHOICES, default=STATE_ACTIVE)

    class Meta:
        db_table = 'tbl_currency'

    def __str__(self):
        return self.country

class RefundLog(models.Model):
    # States
    STATE_INACTIVE = 0
    STATE_ACTIVE = 1
    STATE_DELETED = 2

    STATE_CHOICES = (
        (STATE_INACTIVE, 'New'),
        (STATE_ACTIVE, 'Active'),
        (STATE_DELETED, 'Deleted'),
    )

    reason = models.CharField(max_length=255, blank=True, null=True)
    booking_id = models.IntegerField(blank=True, null=True)
    doctor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='refund_logs_as_doctor')
    credit = models.IntegerField(default=0)
    
    state_id = models.SmallIntegerField(choices=STATE_CHOICES, default=STATE_ACTIVE)
    type_id = models.SmallIntegerField(default=0)

    # Tracking fields
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='refund_logs')

    class Meta:
        db_table = 'tbl_refund_log'

    def __str__(self):
        return self.reason if self.reason else f"RefundLog {self.id}"

class Invoice(models.Model):
    # States
    STATE_INACTIVE = 0
    STATE_ACTIVE = 1
    STATE_DELETED = 2

    STATE_CHOICES = (
        (STATE_INACTIVE, 'New'),
        (STATE_ACTIVE, 'Active'),
        (STATE_DELETED, 'Deleted'),
    )

    # Types
    TYPE_SUBSCRIPTION = 1
    TYPE_VIDEO = 2

    TYPE_CHOICES = (
        (TYPE_SUBSCRIPTION, 'Subscription Invoice'),
        (TYPE_VIDEO, 'Video Plan Invoice'),
    )

    invoice_number = models.CharField(max_length=64)
    subscribed_plan_id = models.IntegerField(blank=True, null=True) # TODO: ForeignKey to SubscribedPlan when created
    file = models.ForeignKey(File, on_delete=models.SET_NULL, null=True, related_name='invoices')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='invoices_received')
    to_email = models.CharField(max_length=128, blank=True, null=True)
    razorpay_invoice_id = models.CharField(max_length=64, blank=True, null=True)
    
    state_id = models.SmallIntegerField(choices=STATE_CHOICES, default=STATE_ACTIVE)
    type_id = models.SmallIntegerField(choices=TYPE_CHOICES, default=TYPE_SUBSCRIPTION)

    # Tracking fields
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='invoices_created')

    class Meta:
        db_table = 'tbl_invoice'

    def __str__(self):
        return self.invoice_number

class HomeContent(models.Model):
    # States
    STATE_INACTIVE = 0
    STATE_ACTIVE = 1
    STATE_DELETED = 2

    STATE_CHOICES = (
        (STATE_INACTIVE, 'New'),
        (STATE_ACTIVE, 'Active'),
        (STATE_DELETED, 'Deleted'),
    )

    # Types
    TYPE_MAIN_CONTENT = 1
    TYPE_SECTION_ONE = 2
    TYPE_SECTION_TWO = 3
    TYPE_SECTION_THREE = 4
    TYPE_SECTION_FOUR = 5

    TYPE_CHOICES = (
        (TYPE_MAIN_CONTENT, 'Main Content'),
        (TYPE_SECTION_ONE, 'Section First'),
        (TYPE_SECTION_TWO, 'Section Second'),
        (TYPE_SECTION_THREE, 'Section Third'),
        (TYPE_SECTION_FOUR, 'Section Fourth'),
    )

    title = models.CharField(max_length=128)
    discription = models.TextField(blank=True, null=True) # retaining typo
    image_file = models.CharField(max_length=255, blank=True, null=True)
    
    state_id = models.SmallIntegerField(choices=STATE_CHOICES, default=STATE_ACTIVE)
    type_id = models.SmallIntegerField(choices=TYPE_CHOICES, unique=True)

    # Tracking fields
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_home_contents')

    class Meta:
        db_table = 'tbl_home_content'

    def __str__(self):
        return self.title

class LoginHistory(models.Model):
    # States
    STATE_FAILED = 0
    STATE_SUCCESS = 1

    STATE_CHOICES = (
        (STATE_FAILED, 'Failed'),
        (STATE_SUCCESS, 'Success'),
    )

    # Types
    TYPE_WEB = 0
    TYPE_AJAX = 1
    TYPE_API = 2

    TYPE_CHOICES = (
        (TYPE_WEB, 'Web'),
        (TYPE_AJAX, 'Ajax'),
        (TYPE_API, 'API'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_histories')
    user_ip = models.CharField(max_length=255)
    user_agent = models.CharField(max_length=255)
    failer_reason = models.CharField(max_length=255, blank=True, null=True) # retaining typo
    code = models.CharField(max_length=255, blank=True, null=True)
    
    login_time = models.DateTimeField(blank=True, null=True)
    logout_time = models.DateTimeField(blank=True, null=True)

    state_id = models.SmallIntegerField(choices=STATE_CHOICES)
    type_id = models.SmallIntegerField(choices=TYPE_CHOICES)

    # Tracking fields
    created_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tbl_login_history'

    def __str__(self):
        return f"Logged-in : {self.user_id} : {self.get_state_id_display()}"
