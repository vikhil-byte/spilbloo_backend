from django.contrib import admin
from .models import Company, CompanyCoupon, MonthlyInvoice, CouponInvoice

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'email', 'state_id', 'created_on')
    list_filter = ('state_id', 'created_on')
    search_fields = ('title', 'email')
    ordering = ('-created_on',)

@admin.register(CompanyCoupon)
class CompanyCouponAdmin(admin.ModelAdmin):
    list_display = ('id', 'company', 'code', 'coupon_type', 'valid_till', 'state_id', 'created_on')
    list_filter = ('state_id', 'created_on')
    search_fields = ('code',)
    ordering = ('-created_on',)
    
    list_select_related = ('company',)
    raw_id_fields = ('company',)

@admin.register(MonthlyInvoice)
class MonthlyInvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'company', 'coupon_code', 'date', 'state_id', 'created_on')
    list_filter = ('state_id', 'date')
    ordering = ('-created_on',)
    
    list_select_related = ('company', 'coupon')
    raw_id_fields = ('company', 'coupon')

@admin.register(CouponInvoice)
class CouponInvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'company', 'invoice_number', 'final_price', 'state_id', 'created_on')
    list_filter = ('state_id', 'date')
    ordering = ('-created_on',)
    
    list_select_related = ('company', 'coupon', 'monthly_invoice')
    raw_id_fields = ('company', 'coupon', 'monthly_invoice')
