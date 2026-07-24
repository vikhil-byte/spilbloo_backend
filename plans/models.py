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
    discounted_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    video_description = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'tbl_plan'


import logging

logger = logging.getLogger(__name__)

class SubscribedPlan(models.Model):
    STATE_CREATED = 0
    STATE_ACTIVE = 1
    STATE_CANCELED = 2
    STATE_PAYMENT_PENDING = 3

    UPCOMING_STATE_NONE = 0
    UPCOMING_STATE_UPCOMING = 2
    UPCOMING_STATE_CANCELED = 4
    UPCOMING_STATE_IMMEDIATE_CANCELED = 5

    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, null=True, blank=True)
    plan_type = models.IntegerField(default=1)
    state_id = models.IntegerField(default=1) # 1=Active, 2=Canceled, 3=Pending
    
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
    coupon_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
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

    created_on = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscribed_plans')


    class Meta:
        db_table = 'tbl_subscribed_plan'

    @property
    def is_terminal(self):
        """Returns True if the subscription is in terminal CANCELED state."""
        return self.state_id == self.STATE_CANCELED

    def activate(self, start_date=None, end_date=None, renewal_date=None, transaction_id=None, plan=None):
        """
        Activates subscription. Fails safely if the subscription is in a terminal CANCELED state.
        """
        if self.is_terminal:
            logger.warning("[SubscribedPlan.activate] Refusing to activate terminal canceled plan id=%s sub_id=%s", self.id, self.subscription_id)
            return False

        self.state_id = self.STATE_ACTIVE
        if plan:
            self.plan = plan
        if start_date:
            self.start_date = start_date
        if end_date:
            self.end_date = end_date
        if renewal_date:
            self.renewal_date = renewal_date
        if transaction_id:
            self.transaction_id = transaction_id
        self.save()
        logger.info("[SubscribedPlan.activate] Activated plan id=%s sub_id=%s state_id=%s", self.id, self.subscription_id, self.state_id)
        return True

    def mark_cancelled(self, immediate=False, reason=None):
        """
        Cancels subscription state cleanly.
        - Sets upcoming_state to UPCOMING_STATE_CANCELED (4).
        - If immediate=True, sets state_id to STATE_CANCELED (2).
        """
        old_state = self.state_id
        old_upcoming = self.upcoming_state
        self.upcoming_state = self.UPCOMING_STATE_CANCELED
        if immediate:
            self.state_id = self.STATE_CANCELED
        if reason:
            self.cancel_reason = reason
        self.save()
        logger.info("[SubscribedPlan.mark_cancelled] sub_id=%s immediate=%s | state_id: %s -> %s | upcoming_state: %s -> %s",
                    self.subscription_id, immediate, old_state, self.state_id, old_upcoming, self.upcoming_state)
        return True

    def mark_pending(self):
        """Sets plan state to PAYMENT_PENDING (3) if not terminal."""
        if self.is_terminal:
            return False
        self.state_id = self.STATE_PAYMENT_PENDING
        self.save()
        return True


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


class WebhookLog(models.Model):
    event = models.CharField(max_length=255, null=True, blank=True)
    subscription_id = models.CharField(max_length=255, null=True, blank=True)
    data = models.TextField(null=True, blank=True)
    created_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tbl_subscription_webhook_log'

