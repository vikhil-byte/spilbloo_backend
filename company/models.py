from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL

class Company(models.Model):
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
    email = models.EmailField(max_length=255, unique=True)
    email_domain = models.CharField(max_length=64, unique=True) # Used for auto-eligibility check
    
    image_file = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    gst_number = models.CharField(max_length=128, blank=True, null=True)
    
    # Geography
    city = models.CharField(max_length=128, blank=True, null=True)
    state = models.CharField(max_length=128, blank=True, null=True)
    country = models.CharField(max_length=128, blank=True, null=True)
    address = models.CharField(max_length=512, blank=True, null=True)
    zipcode = models.CharField(max_length=16, blank=True, null=True)
    contact = models.CharField(max_length=32, blank=True, null=True)
    
    plan_id = models.CharField(max_length=255, blank=True, null=True) # Comma-separated IDs from legacy
    
    state_id = models.SmallIntegerField(choices=STATE_CHOICES, default=STATE_ACTIVE)
    type_id = models.IntegerField(default=0)

    # Tracking fields
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='companies_created')

    class Meta:
        db_table = 'tbl_company'

    def __str__(self):
        return self.title


class CompanyCoupon(models.Model):
    # States
    STATE_INACTIVE = 0
    STATE_ACTIVE = 1
    STATE_DELETED = 2
    STATE_CANCELLED = 3

    STATE_CHOICES = (
        (STATE_INACTIVE, 'New'),
        (STATE_ACTIVE, 'Active'),
        (STATE_DELETED, 'Deleted'),
        (STATE_CANCELLED, 'Cancelled'),
    )

    # Types
    COUPON_TYPE_UNLIMITED = 1
    COUPON_TYPE_LIMITED = 2

    TYPE_CHOICES = (
        (COUPON_TYPE_UNLIMITED, 'Unlimited Period'),
        (COUPON_TYPE_LIMITED, 'Limited Period'),
    )

    code = models.CharField(max_length=255, unique=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='coupons')
    plan_id = models.IntegerField() # Linked to Plan model
    
    # Configuration
    no_of_free_trial_days = models.IntegerField(default=0)
    limit = models.IntegerField(default=0)
    user_limit = models.IntegerField(default=1)
    
    coupon_type = models.IntegerField(choices=TYPE_CHOICES, default=COUPON_TYPE_UNLIMITED)
    state_id = models.SmallIntegerField(choices=STATE_CHOICES, default=STATE_ACTIVE)
    
    valid_till = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True) # Contract end date
    
    # Invoicing helpers from legacy
    one_day_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    no_of_video_session = models.IntegerField(default=0)
    invoice_plan_name = models.CharField(max_length=255, blank=True, null=True)

    # Tracking fields
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='company_coupons_created')

    class Meta:
        db_table = 'tbl_company_coupon'

    def __str__(self):
        return self.code


class MonthlyInvoice(models.Model):
    # States
    STATE_PENDING = 0
    STATE_INITIATED = 1
    STATE_DELETED = 2

    STATE_CHOICES = (
        (STATE_PENDING, 'Pending'),
        (STATE_INITIATED, 'Initiated'),
        (STATE_DELETED, 'Deleted'),
    )

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='monthly_invoices')
    coupon = models.ForeignKey(CompanyCoupon, on_delete=models.CASCADE, related_name='monthly_invoices')
    
    date = models.DateField() # The month of the invoice
    coupon_code = models.CharField(max_length=255)
    
    state_id = models.SmallIntegerField(choices=STATE_CHOICES, default=STATE_PENDING)
    type_id = models.IntegerField(default=0) # Mirroring legacy type_id if needed

    # Tracking fields
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='monthly_invoices_created')

    class Meta:
        db_table = 'tbl_company_monthly_invoice'

    def __str__(self):
        return f"Invoice {self.date} - {self.company.title}"


class CouponInvoice(models.Model):
    # States
    STATE_NEW = 0
    STATE_ACTIVE = 1
    STATE_DELETED = 2

    STATE_CHOICES = (
        (STATE_NEW, 'New'),
        (STATE_ACTIVE, 'Active'),
        (STATE_DELETED, 'Deleted'),
    )

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='coupon_invoices')
    coupon = models.ForeignKey(CompanyCoupon, on_delete=models.CASCADE, related_name='coupon_invoices')
    monthly_invoice = models.ForeignKey(MonthlyInvoice, on_delete=models.CASCADE, related_name='coupon_invoices')
    
    invoice_number = models.CharField(max_length=64, blank=True, null=True)
    date = models.DateField()
    coupon_code = models.CharField(max_length=255)
    
    # Financials
    one_subscription_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    gst_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    final_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    subscription_count = models.IntegerField(default=0)
    subscription_days = models.IntegerField(default=0)
    
    state_id = models.SmallIntegerField(choices=STATE_CHOICES, default=STATE_NEW)
    type_id = models.IntegerField(default=0)
    
    file_id = models.IntegerField(null=True, blank=True) # Linked to File model if it exists

    # Tracking fields
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='coupon_invoices_created')

    class Meta:
        db_table = 'tbl_company_coupon_invoice'

    def __str__(self):
        return f"Final Invoice {self.invoice_number} - {self.company.title}"
