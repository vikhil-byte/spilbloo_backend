from django.urls import path
from .views_notification import NotificationOnOffView, NotificationListView, NotificationReadView

urlpatterns = [
    path('on-off/', NotificationOnOffView.as_view(), name='notification_on_off'),
    path('list/', NotificationListView.as_view(), name='notification_list'),
    path('read/', NotificationReadView.as_view(), name='notification_read'),
]
