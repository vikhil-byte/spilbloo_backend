from rest_framework import serializers
from rest_framework.views import APIView
from .models import DoctorSlot, SlotBooking, Slot, Notification

class SlotSerializer(serializers.ModelSerializer):
    is_selected = serializers.SerializerMethodField()

    class Meta:
        model = Slot
        fields = ('id', 'start_time', 'end_time', 'is_selected')

    def get_is_selected(self, obj):
        request = self.context.get('request')
        start_time = self.context.get('start_time')
        end_time = self.context.get('end_time')
        if start_time and end_time and request and request.user and request.user.is_authenticated:
            return DoctorSlot.objects.filter(
                created_by=request.user,
                availability_slot_id=obj.id,
                start_time__gte=start_time,
                start_time__lte=end_time,
            ).exists()
        return False

class DoctorSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorSlot
        fields = '__all__'
        read_only_fields = ('created_by', 'created_on')

class SlotBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SlotBooking
        fields = '__all__'
        read_only_fields = ('created_by', 'created_on')
