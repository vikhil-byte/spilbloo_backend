from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly
from accounts.permissions import IsAdminUser
from rest_framework.response import Response
from .mixins import StandardizedResponseMixin
from .models import (
    TherapistEarning, ContactForm, DoctorReason, Symptom, DoctorRequest,
    Feed, EmergencyResource, AgeGroup, AssignedTherapist, BestDoctor,
    VideoPlan, VideoCoupon, CouponUser, SubscribedVideo, UserSymptom,
    Setting, Disclaimer, PushNotification, File, Currency, RefundLog, 
    Invoice, HomeContent, LoginHistory
)
from .serializers import (
    TherapistEarningSerializer, ContactFormSerializer, DoctorReasonSerializer, 
    SymptomSerializer, DoctorRequestSerializer, FeedSerializer, 
    EmergencyResourceSerializer, AgeGroupSerializer, AssignedTherapistSerializer, 
    BestDoctorSerializer, VideoPlanSerializer, VideoCouponSerializer, 
    CouponUserSerializer, SubscribedVideoSerializer, UserSymptomSerializer,
    SettingSerializer, DisclaimerSerializer, PushNotificationSerializer, 
    FileSerializer, CurrencySerializer, RefundLogSerializer, InvoiceSerializer, 
    HomeContentSerializer, LoginHistorySerializer
)

class StandardizedModelViewSet(StandardizedResponseMixin, viewsets.ModelViewSet):
    """Base ViewSet that returns standardized responses for all CRUD actions."""
    
    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return self.success_response(data=response.data, message="Data retrieved successfully")

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        return self.success_response(data=response.data, message="Details retrieved successfully")

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return self.success_response(data=response.data, message="Created successfully", status_code=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return self.success_response(data=response.data, message="Updated successfully")

    def partial_update(self, request, *args, **kwargs):
        response = super().partial_update(request, *args, **kwargs)
        return self.success_response(data=response.data, message="Updated successfully")

    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)
        return self.success_response(message="Deleted successfully", status_code=status.HTTP_204_NO_CONTENT)

class TherapistEarningViewSet(StandardizedModelViewSet):
    queryset = TherapistEarning.objects.all()
    serializer_class = TherapistEarningSerializer
    permission_classes = [IsAdminUser]

class ContactFormViewSet(StandardizedModelViewSet):
    queryset = ContactForm.objects.all()
    serializer_class = ContactFormSerializer
    permission_classes = [IsAdminUser] # Hardened: Admin only for viewing apps

class DoctorReasonViewSet(StandardizedModelViewSet):
    queryset = DoctorReason.objects.all()
    serializer_class = DoctorReasonSerializer
    permission_classes = [IsAdminUser]

class SymptomViewSet(StandardizedModelViewSet):
    queryset = Symptom.objects.all()
    serializer_class = SymptomSerializer
    permission_classes = [IsAdminUser]

class DoctorRequestViewSet(StandardizedModelViewSet):
    queryset = DoctorRequest.objects.all()
    serializer_class = DoctorRequestSerializer
    permission_classes = [IsAdminUser]

class FeedViewSet(StandardizedModelViewSet):
    queryset = Feed.objects.all()
    serializer_class = FeedSerializer
    permission_classes = [IsAdminUser]

class EmergencyResourceViewSet(StandardizedModelViewSet):
    queryset = EmergencyResource.objects.all()
    serializer_class = EmergencyResourceSerializer
    permission_classes = [IsAdminUser]

class AgeGroupViewSet(StandardizedModelViewSet):
    queryset = AgeGroup.objects.all()
    serializer_class = AgeGroupSerializer
    permission_classes = [IsAdminUser]

class AssignedTherapistViewSet(StandardizedModelViewSet):
    queryset = AssignedTherapist.objects.all()
    serializer_class = AssignedTherapistSerializer
    permission_classes = [IsAdminUser]

class BestDoctorViewSet(StandardizedModelViewSet):
    queryset = BestDoctor.objects.all()
    serializer_class = BestDoctorSerializer
    permission_classes = [IsAdminUser]

class VideoPlanViewSet(StandardizedModelViewSet):
    queryset = VideoPlan.objects.all()
    serializer_class = VideoPlanSerializer
    permission_classes = [IsAdminUser]

class VideoCouponViewSet(StandardizedModelViewSet):
    queryset = VideoCoupon.objects.all()
    serializer_class = VideoCouponSerializer
    permission_classes = [IsAdminUser]

class CouponUserViewSet(StandardizedModelViewSet):
    queryset = CouponUser.objects.all()
    serializer_class = CouponUserSerializer
    permission_classes = [IsAdminUser]

class SubscribedVideoViewSet(StandardizedModelViewSet):
    queryset = SubscribedVideo.objects.all()
    serializer_class = SubscribedVideoSerializer
    permission_classes = [IsAdminUser]

class UserSymptomViewSet(StandardizedModelViewSet):
    queryset = UserSymptom.objects.all()
    serializer_class = UserSymptomSerializer
    permission_classes = [IsAdminUser]

class SettingViewSet(StandardizedModelViewSet):
    queryset = Setting.objects.all()
    serializer_class = SettingSerializer
    permission_classes = [IsAdminUser]

class DisclaimerViewSet(StandardizedModelViewSet):
    queryset = Disclaimer.objects.all()
    serializer_class = DisclaimerSerializer
    permission_classes = [IsAdminUser]

class PushNotificationViewSet(StandardizedModelViewSet):
    queryset = PushNotification.objects.all()
    serializer_class = PushNotificationSerializer
    permission_classes = [IsAdminUser]

class FileViewSet(StandardizedModelViewSet):
    queryset = File.objects.all()
    serializer_class = FileSerializer
    permission_classes = [IsAdminUser]

class CurrencyViewSet(StandardizedModelViewSet):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer
    permission_classes = [IsAdminUser]

class RefundLogViewSet(StandardizedModelViewSet):
    queryset = RefundLog.objects.all()
    serializer_class = RefundLogSerializer
    permission_classes = [IsAdminUser]

class InvoiceViewSet(StandardizedModelViewSet):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAdminUser]

class HomeContentViewSet(StandardizedModelViewSet):
    queryset = HomeContent.objects.all()
    serializer_class = HomeContentSerializer
    permission_classes = [IsAdminUser]

class LoginHistoryViewSet(StandardizedModelViewSet):
    queryset = LoginHistory.objects.all()
    serializer_class = LoginHistorySerializer
    permission_classes = [IsAdminUser]


# Simple test API with mock data (no DB required)
MOCK_TEST_DATA = [
    {"id": 1, "name": "Test Item One", "active": True},
    {"id": 2, "name": "Test Item Two", "active": True},
    {"id": 3, "name": "Test Item Three", "active": False},
]


@api_view(["GET"])
@permission_classes([AllowAny])
def test_api(request):
    """Test endpoint with mock data to verify API is working."""
    return Response({
        "status": "ok",
        "message": "Test API is working!",
        "data": MOCK_TEST_DATA,
    })
