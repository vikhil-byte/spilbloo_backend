from django.contrib import admin
from .models import Company, CompanyCoupon, MonthlyInvoice, CouponInvoice

# Register your models here.
admin.site.register(Company)
admin.site.register(CompanyCoupon)
admin.site.register(MonthlyInvoice)
admin.site.register(CouponInvoice)
