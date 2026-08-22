from rest_framework import serializers
from .models import DiscoveryBooking


class DiscoveryBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscoveryBooking
        fields = '__all__'
