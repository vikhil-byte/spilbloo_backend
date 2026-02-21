from django.urls import path
from .views import JoinView, LeaveView, CompleteBookingView

urlpatterns = [
    path('join/', JoinView.as_view(), name='join_call'),
    path('leave/', LeaveView.as_view(), name='leave_call'),
    path('complete-booking/', CompleteBookingView.as_view(), name='complete_booking'),
]
