from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.contrib.auth import get_user_model

User = get_user_model()

class NotificationOnOffView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user = request.user
        
        # In PHP, NOTIFICATION_ON is likely 1 and OFF is 0
        current_state = getattr(user, 'is_notify', 1)

        if current_state == 1:
            msg = 'off'
            new_state = 0
        else:
            msg = 'on'
            new_state = 1
        
        # Depending on how the User model is implemented in accounts/models.py
        # Assuming is_notify field exists
        if hasattr(user, 'is_notify'):
            user.is_notify = new_state
            user.save(update_fields=['is_notify'])

        return Response({
            "message": f"Notification is {msg}",
            "is_notify": new_state
        }, status=status.HTTP_200_OK)
