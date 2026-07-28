from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL

class DoctorSlot(models.Model):
    availability_doctor_id = models.IntegerField(null=True, blank=True)
    availability_slot_id = models.IntegerField(null=True, blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    state_id = models.IntegerField(default=1)
    type_id = models.IntegerField(default=0)
    
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='doctor_slots')

    class Meta:
        db_table = 'tbl_doctor_slot'

class SlotBooking(models.Model):
    # Align with legacy PHP SlotBooking + iOS BookingState (0..3).
    STATE_REQUEST = 0
    STATE_ACCEPT = 1
    STATE_CANCELED = 2
    STATE_COMPLETED = 3

    STATE_CHOICES = (
        (STATE_REQUEST, "Request"),
        (STATE_ACCEPT, "Accept"),
        (STATE_CANCELED, "Canceled"),
        (STATE_COMPLETED, "Completed"),
    )

    UPCOMING_BOOKING = 1
    COMPLETED_BOOKING = 2

    slot_id = models.IntegerField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    doctor_id = models.IntegerField()
    date = models.DateField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    room_id = models.CharField(max_length=255, blank=True, default="")
    state_id = models.IntegerField(choices=STATE_CHOICES, default=STATE_REQUEST)
    type_id = models.IntegerField(default=0)
    is_active = models.IntegerField(default=0)
    is_call_end = models.IntegerField(default=0)
    call_duration = models.CharField(max_length=16, null=True, blank=True, default='00:00:00')
    duration_millisec = models.CharField(max_length=32, null=True, blank=True, default='')

    cancel_reason = models.CharField(max_length=255, null=True, blank=True)
    complete_reason = models.CharField(max_length=255, null=True, blank=True)
    is_refunded = models.IntegerField(default=0)

    doctor_reschedule = models.IntegerField(default=0)
    patient_reschedule = models.IntegerField(default=0)
    old_start_time = models.DateTimeField(null=True, blank=True)
    old_end_time = models.DateTimeField(null=True, blank=True)
    old_date = models.DateField(null=True, blank=True)
    is_reschedule_confirm = models.IntegerField(default=0)

    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='slot_bookings')

    class Meta:
        db_table = 'tbl_slot_booking'

class Slot(models.Model):
    title = models.CharField(max_length=255)
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_gap_time = models.IntegerField(null=True, blank=True)
    state_id = models.IntegerField(default=1)
    type_id = models.IntegerField(default=0)
    created_on = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='slots')

    class Meta:
        db_table = 'tbl_slot'

class Notification(models.Model):
    title = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    model_id = models.IntegerField(null=True, blank=True)
    model_type = models.CharField(max_length=255, null=True, blank=True)
    is_read = models.IntegerField(default=0)
    state_id = models.IntegerField(default=0)
    type_id = models.IntegerField(default=0)
    to_user_id = models.IntegerField()
    
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
