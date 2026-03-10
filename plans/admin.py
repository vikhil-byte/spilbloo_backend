from django.contrib import admin
from .models import Plan, SubscribedPlan

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('title', 'plan_id', 'final_price', 'duration', 'state_id')
    search_fields = ('title', 'plan_id')
    list_filter = ('state_id', 'plan_type')

@admin.register(SubscribedPlan)
class SubscribedPlanAdmin(admin.ModelAdmin):
    list_display = ('id', 'subscription_id', 'plan', 'created_by', 'state_id', 'created_on')
    search_fields = ('subscription_id', 'created_by__email')
    list_filter = ('state_id', 'plan_type', 'created_on')
    readonly_fields = ('created_on',)
