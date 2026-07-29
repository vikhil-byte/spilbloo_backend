import math
from decimal import Decimal, InvalidOperation

from django.utils.html import strip_tags
from rest_framework import serializers

from company.models import CompanyCoupon
from core.models import VideoPlan, SubscribedVideo, VideoCoupon, CouponUser
from .models import Plan, SubscribedPlan, Coupon


def _strip_html_text(value):
    """Mirror PHP Plan::removeTags() for API payloads."""
    if value is None:
        return ""
    return strip_tags(str(value)).strip()


def _discounted_price_calculated(discounted_price, duration):
    """Mirror PHP: ceil(((int)$discounted_price / 7) * (int)$duration)."""
    try:
        discounted = int(Decimal(str(discounted_price or 0)))
    except (InvalidOperation, ValueError, TypeError):
        discounted = 0
    try:
        days = int(duration or 0)
    except (ValueError, TypeError):
        days = 0
    if days <= 0:
        return 0
    return int(math.ceil((discounted / 7.0) * days))


class PlanSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    video_description = serializers.SerializerMethodField()
    discounted_price_calculated = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = (
            "id",
            "plan_id",
            "title",
            "company_name",
            "image_file",
            "description",
            "video_description",
            "duration",
            "weekly_price",
            "discounted_price",
            "discounted_price_calculated",
            "tax_price",
            "tax_percentage",
            "final_price",
            "total_price",
            "doctor_price",
            "incentive_days",
            "no_of_free_trial_days",
            "no_of_video_session",
            "plan_type",
            "is_recommended",
            "state_id",
            "type_id",
            "currency_code",
        )

    def get_title(self, obj):
        company = self.context.get("company")
        if company is not None:
            coupon = (
                CompanyCoupon.objects.filter(company=company, plan_id=obj.id)
                .exclude(invoice_plan_name__isnull=True)
                .exclude(invoice_plan_name="")
                .first()
            )
            if coupon and coupon.invoice_plan_name:
                return coupon.invoice_plan_name
        return obj.title

    def get_company_name(self, obj):
        company = self.context.get("company")
        if company is not None:
            return company.title or ""
        return ""

    def get_description(self, obj):
        return _strip_html_text(obj.description)

    def get_video_description(self, obj):
        return _strip_html_text(obj.video_description)

    def get_discounted_price_calculated(self, obj):
        return _discounted_price_calculated(obj.discounted_price, obj.duration)


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
