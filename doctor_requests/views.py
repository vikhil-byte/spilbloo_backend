from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from core.models import DoctorReason, DoctorRequest
from availability.models import SlotBooking
from .serializers import DoctorReasonSerializer

class ReasonListView(generics.ListAPIView):
    permission_classes = (AllowAny,) # PHP allowed patient, let's keep AllowAny or IsAuthenticated
    serializer_class = DoctorReasonSerializer

    def get_queryset(self):
        return DoctorReason.objects.filter(state_id=1).order_by('-id')

class SendRequestView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        reason_id = request.data.get('reason_id') # assuming reason is sent as ID
        description = request.data.get('description')
        
        # In PHP, doctor_id comes from \Yii::$app->user->identity->doctor_id
        # Assuming the User model has doctor_id or a related profile
        user = request.user
        doctor_id = getattr(user, 'doctor_id', None)

        try:
            reason = DoctorReason.objects.get(id=reason_id)
            doc_req = DoctorRequest.objects.create(
                reason=reason,
                description=description,
                doctor_id=doctor_id,
                state_id=0, # INACTIVE
                created_by=user
            )
            return Response({"message": "Your request submitted successfully."}, status=status.HTTP_200_OK)
        except DoctorReason.DoesNotExist:
            return Response({"error": "Invalid reason ID"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class CheckIsAllowedView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user = request.user
        doctor_id = getattr(user, 'doctor_id', None)
        
        booking = SlotBooking.objects.filter(
            created_by=user,
            doctor_id=doctor_id,
            state_id__in=[2, 3] # REQUEST, ACCEPT
        ).first()

        if booking:
            return Response({"error": "You have an active booking with your current therapist. Please try after the booking is completed."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"message": "You can change the therapist."}, status=status.HTTP_200_OK)
