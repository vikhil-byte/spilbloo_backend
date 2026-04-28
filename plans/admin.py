from django.contrib import admin
from .models import Plan, SubscribedPlan, Coupon


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "plan_id",
        "currency_code",
        "final_price",
        "plan_type",
        "type_id",
        "state_id",
        "is_recommended",
    )
    search_fields = ("title", "plan_id", "currency_code")
    list_filter = ("currency_code", "state_id", "plan_type", "type_id", "is_recommended")


@admin.register(SubscribedPlan)
class SubscribedPlanAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created_by",
        "plan",
        "subscription_id",
        "state_id",
        "plan_type",
        "final_price",
    )
    search_fields = ("subscription_id", "transaction_id", "created_by__email", "plan__plan_id")
    list_filter = ("state_id", "plan_type")


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "type_id", "discount", "no_of_free_trial_days", "state_id", "valid_till")
    search_fields = ("code", "plan_id")
    list_filter = ("state_id", "type_id")
