from django.contrib import admin
from .models import (
    TherapistEarning, ContactForm, DoctorReason, Symptom, DoctorRequest,
    Feed, EmergencyResource, AgeGroup, AssignedTherapist, BestDoctor,
    VideoPlan, VideoCoupon, CouponUser, SubscribedVideo, UserSymptom,
    Currency, RefundLog, Invoice, HomeContent, LoginHistory
)

# Register your models here.
admin.site.register(TherapistEarning)
admin.site.register(ContactForm)
admin.site.register(DoctorReason)
admin.site.register(Symptom)
admin.site.register(DoctorRequest)
admin.site.register(Feed)
admin.site.register(EmergencyResource)
admin.site.register(AgeGroup)
admin.site.register(AssignedTherapist)
admin.site.register(BestDoctor)
admin.site.register(VideoPlan)
admin.site.register(VideoCoupon)
admin.site.register(CouponUser)
admin.site.register(SubscribedVideo)
admin.site.register(UserSymptom)
admin.site.register(Currency)
admin.site.register(RefundLog)
admin.site.register(Invoice)
admin.site.register(HomeContent)
admin.site.register(LoginHistory)
