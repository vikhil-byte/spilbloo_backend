from rest_framework import serializers
from .models import Plan, SubscribedPlan, Coupon
from core.models import VideoPlan, SubscribedVideo, VideoCoupon, CouponUser

class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = '__all__'

class SubscribedPlanSerializer(serializers.ModelSerializer):
    plan_title = serializers.CharField(source='plan.title', read_only=True)
    state = serializers.SerializerMethodField()
    readable_plan_type = serializers.SerializerMethodField()
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)

    class Meta:
        model = SubscribedPlan
        fields = '__all__'

    def get_state(self, obj):
        # 0=Created, 1=Active, 2=Cancelled, 3=Trial, etc. (Matching SubscriptionsPage.jsx expectations)
        mapping = {0: 'Created', 1: 'Active', 2: 'Cancelled', 3: 'Trial'}
        return mapping.get(obj.state_id, 'Unknown')

    def get_readable_plan_type(self, obj):
        # 0=Free, 1=Paid
        mapping = {0: 'Free', 1: 'Paid'}
        return mapping.get(obj.plan_type, 'Unknown')

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
