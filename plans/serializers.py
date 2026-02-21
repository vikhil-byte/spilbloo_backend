from rest_framework import serializers
from .models import Plan, SubscribedPlan, Coupon
from core.models import VideoPlan, SubscribedVideo, VideoCoupon, CouponUser

class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = '__all__'

class SubscribedPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscribedPlan
        fields = '__all__'

class VideoPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoPlan
        fields = '__all__'

class SubscribedVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscribedVideo
        fields = '__all__'

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = '__all__'

class VideoCouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoCoupon
        fields = '__all__'

class CouponUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CouponUser
        fields = '__all__'
