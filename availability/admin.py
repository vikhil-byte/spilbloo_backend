from django.contrib import admin
from .models import DoctorSlot, SlotBooking, Slot, Notification, PrescriptionUpload

@admin.register(DoctorSlot)
class DoctorSlotAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_by', 'availability_slot_id', 'start_time', 'end_time', 'state_id', 'created_on')
    list_filter = ('state_id', 'created_on')
    ordering = ('-created_on',)
    
    list_select_related = ('created_by',)
    raw_id_fields = ('created_by',)

@admin.register(SlotBooking)
class SlotBookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_by', 'doctor_id', 'slot_id', 'start_time', 'end_time', 'state_id', 'created_on')
    list_filter = ('state_id', 'created_on')
    ordering = ('-created_on',)
    
    list_select_related = ('created_by',)
    raw_id_fields = ('created_by',)

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
