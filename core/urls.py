from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TherapistEarningViewSet, SlotBookingViewSet, ContactFormViewSet, DoctorReasonViewSet,
    SymptomViewSet, DoctorRequestViewSet, FeedViewSet,
    EmergencyResourceViewSet, AgeGroupViewSet, AssignedTherapistViewSet,
    BestDoctorViewSet, VideoPlanViewSet, VideoCouponViewSet,
    CouponUserViewSet, SubscribedVideoViewSet, UserSymptomViewSet,
    SettingViewSet, DisclaimerViewSet, PushNotificationViewSet,
    FileViewSet, CurrencyViewSet, RefundLogViewSet, InvoiceViewSet,
    HomeContentViewSet, LoginHistoryViewSet
)

router = DefaultRouter()
router.register(r'therapist-earnings', TherapistEarningViewSet)
router.register(r'slot-bookings', SlotBookingViewSet)
router.register(r'contact-forms', ContactFormViewSet)
router.register(r'doctor-reasons', DoctorReasonViewSet)
router.register(r'symptoms', SymptomViewSet)
router.register(r'doctor-requests', DoctorRequestViewSet)
router.register(r'feeds', FeedViewSet)
router.register(r'emergency-resources', EmergencyResourceViewSet)
router.register(r'age-groups', AgeGroupViewSet)
router.register(r'assigned-therapists', AssignedTherapistViewSet)
router.register(r'best-doctors', BestDoctorViewSet)
router.register(r'video-plans', VideoPlanViewSet)
router.register(r'video-coupons', VideoCouponViewSet)
router.register(r'coupon-users', CouponUserViewSet)
router.register(r'subscribed-videos', SubscribedVideoViewSet)
router.register(r'user-symptoms', UserSymptomViewSet)
router.register(r'settings', SettingViewSet)
router.register(r'disclaimers', DisclaimerViewSet)
router.register(r'push-notifications', PushNotificationViewSet)
router.register(r'files', FileViewSet)
router.register(r'currencies', CurrencyViewSet)
router.register(r'refund-logs', RefundLogViewSet)
router.register(r'invoices', InvoiceViewSet)
router.register(r'home-contents', HomeContentViewSet)
router.register(r'login-histories', LoginHistoryViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
