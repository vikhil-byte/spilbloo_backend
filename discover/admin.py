from django.contrib import admin
from .models import DiscoveryBooking


@admin.register(DiscoveryBooking)
class DiscoveryBookingAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'created_by', 'assigned_doctor', 'start_time', 'amount',
        'state_id', 'refund_eligible_until', 'created_on',
    )
    list_filter = ('state_id', 'created_on')
    search_fields = ('created_by__email', 'assigned_doctor__email', 'razorpay_order_id', 'razorpay_payment_id')
    ordering = ('-created_on',)
    list_select_related = ('created_by', 'assigned_doctor')
    raw_id_fields = ('created_by', 'assigned_doctor')
    readonly_fields = ('created_on',)
