from rest_framework import serializers
from .models import Call


class CallSerializer(serializers.ModelSerializer):
    user_id = serializers.PrimaryKeyRelatedField(source='user', read_only=True)
    created_by_id = serializers.PrimaryKeyRelatedField(source='created_by', read_only=True)

    class Meta:
        model = Call
        fields = (
            'id', 'booking_id', 'user_id', 'session_id', 'call_end_id',
            'token', 'start_time', 'end_time', 'duration', 'duration_millisec',
            'state_id', 'type_id', 'created_on', 'created_by_id',
        )
