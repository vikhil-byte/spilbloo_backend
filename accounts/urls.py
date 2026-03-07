from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, CustomTokenObtainPairView, AdminLoginView, UserProfileView,
    VerifyOtpView, ResendOtpView, DoctorContactView,
    CheckView, LogoutView, ChangePasswordView, DetailView, GetPageView,
    ForgotPasswordView, SymptomListView, MatchesListView, FaqView, AssignDoctorView,
    AssignVideoDoctorView, SocialLoginView, EarningsView, AcceptConsentView, SendMessageView,
    UserListView, UserDetailView, UserUpdateView,
    AuditLogListView, LoginHistoryListView
)
from .views_notification import NotificationOnOffView

urlpatterns = [
    path('signup/', RegisterView.as_view(), name='auth_register'),
    path('verify-otp/', VerifyOtpView.as_view(), name='verify_otp'),
    path('resend-otp/', ResendOtpView.as_view(), name='resend_otp'),
    path('doctor-contact/', DoctorContactView.as_view(), name='doctor_contact'),
    path('check/', CheckView.as_view(), name='check'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('detail/', DetailView.as_view(), name='user_detail'),
    path('detail/<int:pk>/', DetailView.as_view(), name='user_detail_pk'),
    path('get-page/', GetPageView.as_view(), name='get_page'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('symptom-list/', SymptomListView.as_view(), name='symptom_list'),
    path('matches-list/', MatchesListView.as_view(), name='matches_list'),
    path('faq/', FaqView.as_view(), name='faq'),
    path('assign-doctor/', AssignDoctorView.as_view(), name='assign_doctor'),
    path('assign-video-doctor/', AssignVideoDoctorView.as_view(), name='assign_video_doctor'),
    path('social-login/', SocialLoginView.as_view(), name='social_login'),
    path('earnings/', EarningsView.as_view(), name='earnings'),
    path('accept-consent/', AcceptConsentView.as_view(), name='accept_consent'),
    path('send-message/', SendMessageView.as_view(), name='send_message'),
    path('users/', UserListView.as_view(), name='user_list'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user_detail'),
    path('users/<int:pk>/update/', UserUpdateView.as_view(), name='user_update'),
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('admin-login/', AdminLoginView.as_view(), name='admin_login'),
    path('login/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('update-profile/', UserProfileView.as_view(), name='user_profile'),
    path('audit-logs/', AuditLogListView.as_view(), name='audit_log_list'),
    path('login-history-list/', LoginHistoryListView.as_view(), name='login_history_list'),
]
