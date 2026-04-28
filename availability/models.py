from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL

class DoctorSlot(models.Model):
    availability_slot_id = models.IntegerField(null=True, blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    state_id = models.IntegerField(default=1)
    
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='doctor_slots')

    class Meta:
        db_table = 'tbl_doctor_slot'

class SlotBooking(models.Model):
    slot_id = models.IntegerField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    doctor_id = models.IntegerField()
    state_id = models.IntegerField(default=2) # 2 = REQUEST, 3 = ACCEPT, 4 = CANCELLED, etc.
    type_id = models.IntegerField(default=0)
    is_active = models.IntegerField(default=0)
    
    cancel_reason = models.CharField(max_length=255, null=True, blank=True)
    is_refunded = models.IntegerField(default=0)
    
    doctor_reschedule = models.IntegerField(default=0)
    patient_reschedule = models.IntegerField(default=0)
    old_start_time = models.DateTimeField(null=True, blank=True)
    old_end_time = models.DateTimeField(null=True, blank=True)
    is_reschedule_confirm = models.IntegerField(default=0)

    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='slot_bookings')

    class Meta:
        db_table = 'tbl_slot_booking'

class Slot(models.Model):
    title = models.CharField(max_length=255)
    start_time = models.TimeField()
    end_time = models.TimeField()
    state_id = models.IntegerField(default=1)

    class Meta:
        db_table = 'tbl_slot'

class Notification(models.Model):
    html = models.TextField(null=True, blank=True)
    title = models.CharField(max_length=255, null=True, blank=True)
    to_user_id = models.IntegerField()
    model_type = models.CharField(max_length=255, null=True, blank=True)
    is_read = models.IntegerField(default=0)
    
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications_created')

    class Meta:
        db_table = 'tbl_notification'


class PrescriptionUpload(models.Model):
    booking_id = models.IntegerField()
    notes = models.TextField(null=True, blank=True)
    file = models.FileField(upload_to="prescriptions/", null=True, blank=True)

    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="prescription_uploads")

    class Meta:
        db_table = "tbl_prescription_upload"
