from django.urls import path
from .views import (
    AddScheduleView, UpdateScheduleView, GetDoctorSlotView, BookingView,
    DoctorBookingListView, PatientBookingListView, DoctorBookingReqView,
    NotificationCountView, AcceptBookingView, DoctorRescheduleView,
    DoctorCancelView, PatientRescheduleView, ConfirmRescheduleView
)

urlpatterns = [
    path('add-schedule/', AddScheduleView.as_view(), name='add_schedule'),
    path('add-multiple-schedule/', AddScheduleView.as_view(), name='add_multiple_schedule'), # Reusing AddScheduleView if it handles multiple
    path('schedules-info/', GetDoctorSlotView.as_view(), name='schedules_info'), # Reusing GetDoctorSlotView
    path('book-list/', PatientBookingListView.as_view(), name='book_list'),
    path('update-schedule/', UpdateScheduleView.as_view(), name='update_schedule'),
    path('get-schedule-slot/', GetDoctorSlotView.as_view(), name='get_schedule_slot'),
    path('book/', BookingView.as_view(), name='book'),
    path('appointment/', DoctorBookingReqView.as_view(), name='appointment'),
    path('appointment-list/', DoctorBookingListView.as_view(), name='appointment_list'),
    path('complete/', AcceptBookingView.as_view(), name='complete'), # Complete logic might be shared
    path('cancel/', DoctorCancelView.as_view(), name='cancel'),
    path('upload-presciption/', AcceptBookingView.as_view(), name='upload_presciption'), # Placeholder
    path('check-session/', BookingView.as_view(), name='check_session'), # Placeholder
    path('check-video-link/', BookingView.as_view(), name='check_video_link'), # Placeholder
    path('notification-count/', NotificationCountView.as_view(), name='notification_count'),
    path('accept-booking/', AcceptBookingView.as_view(), name='accept_booking'),
    path('doctor-reschedule/', DoctorRescheduleView.as_view(), name='doctor_reschedule'),
    path('doctor-cancel/', DoctorCancelView.as_view(), name='doctor_cancel'),
    path('patient-reschedule/', PatientRescheduleView.as_view(), name='patient_reschedule'),
    path('confirm-reschedule/', ConfirmRescheduleView.as_view(), name='confirm_reschedule'),
]
