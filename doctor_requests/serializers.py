from rest_framework import serializers
from core.models import DoctorReason, DoctorRequest

class DoctorReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorReason
        fields = '__all__'

class DoctorRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorRequest
        fields = '__all__'
