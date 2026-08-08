from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from availability.models import Notification

User = get_user_model()

class NotificationOnOffView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user = request.user
        
        current_state = getattr(user, 'is_notify', 1)

        if current_state == 1:
            msg = 'off'
            new_state = 0
        else:
            msg = 'on'
            new_state = 1
        
        if hasattr(user, 'is_notify'):
            user.is_notify = new_state
            user.save(update_fields=['is_notify'])

        return Response({
            "message": f"Notification is {msg}",
            "is_notify": new_state
        }, status=status.HTTP_200_OK)


class NotificationListView(APIView):
    """
    Returns user inbox notifications matching legacy PHP /api/notification/list/
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user = request.user
        notifications = Notification.objects.filter(to_user_id=user.id).order_by('-created_on')
        
        results = []
        unread_count = 0
        for n in notifications:
            if n.is_read == 0:
                unread_count += 1
            results.append({
                "id": n.id,
                "title": n.title or "",
                "description": n.description or "",
                "model_id": n.model_id,
                "model_type": n.model_type or "",
                "is_read": n.is_read,
                "state_id": n.state_id,
                "type_id": n.type_id,
                "to_user_id": n.to_user_id,
                "created_on": n.created_on.strftime("%Y-%m-%d %H:%M:%S") if n.created_on else "",
            })

        return Response({
            "status": "success",
            "unread_count": unread_count,
            "list": results
        }, status=status.HTTP_200_OK)


class NotificationReadView(APIView):
    """
    Marks notification(s) as read matching legacy PHP /api/notification/read/
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        user = request.user
        notification_id = request.data.get('id')
        mark_all = request.data.get('mark_all', False)

        if mark_all:
            updated_count = Notification.objects.filter(to_user_id=user.id, is_read=0).update(is_read=1)
            return Response({
                "status": "success",
                "message": f"Marked {updated_count} notifications as read."
            }, status=status.HTTP_200_OK)

        if not notification_id:
            return Response({"error": "Notification id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            notification = Notification.objects.get(id=notification_id, to_user_id=user.id)
            notification.is_read = 1
            notification.save(update_fields=['is_read'])
            return Response({
                "status": "success",
                "message": "Notification marked as read."
            }, status=status.HTTP_200_OK)
        except Notification.DoesNotExist:
            return Response({"error": "Notification not found."}, status=status.HTTP_404_NOT_FOUND)
