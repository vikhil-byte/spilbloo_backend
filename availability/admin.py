from django.contrib import admin
from .models import DoctorSlot, SlotBooking, Slot, Notification, PrescriptionUpload

# Register your models here.
admin.site.register(DoctorSlot)
admin.site.register(SlotBooking)
admin.site.register(Slot)
admin.site.register(Notification)
admin.site.register(PrescriptionUpload)
