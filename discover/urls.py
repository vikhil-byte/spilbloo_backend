from django.urls import path
from .views import (
    AvailableSlotsView, CreateOrderView, VerifyPaymentView,
    PatientCancelDiscoveryView, TherapistCancelDiscoveryView, MarkNoShowView,
    DiscoveryWebhookView,
)

urlpatterns = [
    path('available-slots/', AvailableSlotsView.as_view(), name='discover_available_slots'),
    path('create-order/', CreateOrderView.as_view(), name='discover_create_order'),
    path('verify-payment/', VerifyPaymentView.as_view(), name='discover_verify_payment'),
    path('cancel/', PatientCancelDiscoveryView.as_view(), name='discover_patient_cancel'),
    path('therapist-cancel/', TherapistCancelDiscoveryView.as_view(), name='discover_therapist_cancel'),
    path('mark-no-show/', MarkNoShowView.as_view(), name='discover_mark_no_show'),
    path('razorpay-webhook/', DiscoveryWebhookView.as_view(), name='discover_webhook'),
]
