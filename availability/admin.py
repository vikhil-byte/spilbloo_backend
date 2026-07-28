from django.contrib import admin
from .models import DoctorSlot, SlotBooking, Slot, Notification, PrescriptionUpload
from core.models import RefundLog

@admin.register(DoctorSlot)
class DoctorSlotAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_by', 'availability_slot_id', 'start_time', 'end_time', 'state_id', 'created_on')
    list_filter = ('state_id', 'created_on')
    ordering = ('-created_on',)
    
    list_select_related = ('created_by',)
    raw_id_fields = ('created_by',)

@admin.register(SlotBooking)
class SlotBookingAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'created_by', 'doctor_id', 'slot_id', 'room_id',
        'start_time', 'end_time', 'state_id', 'is_refunded',
        'is_active', 'created_on',
    )
    list_filter = ('state_id', 'is_refunded', 'created_on')
    ordering = ('-created_on',)
    list_select_related = ('created_by',)
    raw_id_fields = ('created_by',)
    search_fields = ('room_id', 'created_by__email', 'created_by__first_name')
    date_hierarchy = 'created_on'
    readonly_fields = (
        'room_id', 'is_call_end', 'complete_reason', 'is_refunded',
        'cancel_reason', 'doctor_reschedule', 'patient_reschedule',
        'old_start_time', 'old_end_time', 'is_reschedule_confirm',
    )
    actions = ('refund_bookings',)

    @admin.action(description='Refund 1 video credit to patient(s)')
    def refund_bookings(self, request, queryset):
        refunded = 0
        skipped = 0
        for booking in queryset:
            if booking.is_refunded:
                skipped += 1
                continue

            booking.is_refunded = 1
            if booking.state_id != SlotBooking.STATE_CANCELED:
                booking.state_id = SlotBooking.STATE_CANCELED
                booking.cancel_reason = 'Refunded by admin'
                booking.save(update_fields=['is_refunded', 'state_id', 'cancel_reason'])
            else:
                booking.save(update_fields=['is_refunded'])

            user = booking.created_by
            if user:
                user.video_credit = (user.video_credit or 0) + 1
                user.save(update_fields=['video_credit'])

            RefundLog.objects.create(
                reason='Admin manual refund',
                booking_id=booking.id,
                doctor_id=booking.doctor_id,
                created_by_id=booking.created_by_id,
                credit=1,
            )
            refunded += 1

        msg_parts = []
        if refunded:
            msg_parts.append(f'{refunded} booking(s) refunded.')
        if skipped:
            msg_parts.append(f'{skipped} already refunded — skipped.')
        self.message_user(request, ' '.join(msg_parts))

@admin.register(Slot)
class SlotAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'start_time', 'end_time', 'state_id')
    list_filter = ('state_id',)
    search_fields = ('title',)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'to_user_id', 'title', 'model_type', 'is_read', 'created_on', 'created_by')
    list_filter = ('is_read', 'created_on')
    search_fields = ('title', 'html')
    ordering = ('-created_on',)
    
    # Query optimizations for large notification logs
    show_full_result_count = False
    list_select_related = ('created_by',)
    raw_id_fields = ('created_by',)

@admin.register(PrescriptionUpload)
class PrescriptionUploadAdmin(admin.ModelAdmin):
    list_display = ('id', 'booking_id', 'created_by', 'created_on')
    ordering = ('-created_on',)
    
    list_select_related = ('created_by',)
    raw_id_fields = ('created_by',)
