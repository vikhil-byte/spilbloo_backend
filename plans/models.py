from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL

class Plan(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    plan_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    no_of_video_session = models.IntegerField(default=0)
    no_of_free_trial_days = models.IntegerField(default=0)
    currency_code = models.CharField(max_length=10, default='INR')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    final_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    doctor_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    duration = models.IntegerField(default=30) # in days
    plan_type = models.IntegerField(default=1) # 1=Paid, 0=Free
    type_id = models.IntegerField(default=1) # Visibility
    state_id = models.IntegerField(default=1) # 1=Active
    is_recommended = models.IntegerField(default=0)
    incentive_days = models.IntegerField(default=0)

    class Meta:
        db_table = 'tbl_plan'

class SubscribedPlan(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, null=True, blank=True)
    plan_type = models.IntegerField(default=1)
    state_id = models.IntegerField(default=1) # 1=Active, etc...
    
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    renewal_date = models.DateTimeField(null=True, blank=True)
    
    subscription_id = models.CharField(max_length=255, null=True, blank=True)
    transaction_id = models.CharField(max_length=255, null=True, blank=True)
    customer_id = models.CharField(max_length=255, null=True, blank=True)
    
    plan_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    gst_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    final_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    coupon = models.CharField(max_length=255, null=True, blank=True)
    coupon_free_trial_days = models.IntegerField(default=0)
    company_coupon = models.ForeignKey('company.CompanyCoupon', on_delete=models.SET_NULL, null=True, blank=True, related_name='subscriptions')
    type_id = models.IntegerField(default=0) # Coupon applied/not applied

    address = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    state = models.CharField(max_length=255, null=True, blank=True)
    country = models.CharField(max_length=255, null=True, blank=True)
    contact = models.CharField(max_length=255, null=True, blank=True)

    cancel_reason = models.CharField(max_length=255, null=True, blank=True)
    
    upcoming_plan_id = models.IntegerField(null=True, blank=True)
    upcoming_state = models.IntegerField(default=0)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscribed_plans')

    class Meta:
        db_table = 'tbl_subscribed_plan'

class Coupon(models.Model):
    code = models.CharField(max_length=255, unique=True)
    plan_id = models.CharField(max_length=255, null=True, blank=True) # Could be comma separated
    type_id = models.IntegerField(default=0) # Flat/Percent/FreeTrial
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    no_of_free_trial_days = models.IntegerField(default=0)
    limit = models.IntegerField(default=0)
    user_limit = models.IntegerField(default=1)
    valid_till = models.DateTimeField(null=True, blank=True)
    state_id = models.IntegerField(default=1)

    class Meta:
        db_table = 'tbl_coupon'
