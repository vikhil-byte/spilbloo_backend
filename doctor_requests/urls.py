from django.urls import path
from .views import ReasonListView, SendRequestView, CheckIsAllowedView

urlpatterns = [
    path('reason-list/', ReasonListView.as_view(), name='reason_list'),
    path('send/', SendRequestView.as_view(), name='send_request'),
    path('check-is-allowed/', CheckIsAllowedView.as_view(), name='check_is_allowed'),
]
