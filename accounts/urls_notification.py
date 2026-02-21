from django.urls import path
from .views_notification import NotificationOnOffView

urlpatterns = [
    path('on-off/', NotificationOnOffView.as_view(), name='notification_on_off'),
]
