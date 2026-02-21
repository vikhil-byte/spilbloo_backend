from rest_framework import serializers
from rest_framework.views import APIView
from .models import DoctorSlot, SlotBooking, Slot, Notification

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
