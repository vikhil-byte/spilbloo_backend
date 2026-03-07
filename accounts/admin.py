from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, HaLogins


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        'email',
        'full_name',
        'get_role_display',
        'get_state_display',
        'is_staff',
        'is_active',
        'date_joined',
        'last_visit_time',
    ]
    list_filter = ['role_id', 'state_id', 'is_staff', 'is_active', 'is_superuser']
    search_fields = ['email', 'full_name', 'contact_no', 'city', 'country']
    ordering = ['-date_joined']
    list_per_page = 25

    fieldsets = (
        (None, {
            'fields': ('email', 'password'),
        }),
        ('Identity', {
            'fields': ('full_name', 'date_of_birth', 'gender', 'about_me', 'profile_file'),
        }),
        ('Contact & location', {
            'fields': ('contact_no', 'address', 'city', 'country', 'zipcode', 'latitude', 'longitude'),
        }),
        ('Account type & status', {
            'fields': ('role_id', 'state_id', 'type_id', 'is_staff', 'is_superuser', 'is_active'),
        }),
        ('Preferences', {
            'fields': ('language', 'timezone', 'tos'),
        }),
        ('Security & activity', {
            'fields': (
                'last_visit_time', 'last_action_time', 'last_password_change',
                'login_error_count', 'activation_key',
            ),
        }),
        ('Audit', {
            'fields': ('created_on', 'updated_on', 'created_by_id'),
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'password1', 'password2'),
        }),
        ('Account type', {
            'fields': ('role_id', 'state_id', 'is_staff', 'is_superuser', 'is_active'),
        }),
    )

    readonly_fields = [
        'last_visit_time', 'last_action_time', 'last_password_change',
        'created_on', 'updated_on',
    ]

    def get_role_display(self, obj):
        if obj is None:
            return '-'
        return obj.get_role_id_display() or str(obj.role_id)
    get_role_display.short_description = 'Role'

    def get_state_display(self, obj):
        if obj is None:
            return '-'
        label = obj.get_state_id_display() or str(obj.state_id)
        if obj.state_id == User.STATE_ACTIVE:
            return format_html('<span style="color: green;">{}</span>', label)
        if obj.state_id == User.STATE_BANNED:
            return format_html('<span style="color: red;">{}</span>', label)
        if obj.state_id == User.STATE_INACTIVE:
            return format_html('<span style="color: gray;">{}</span>', label)
        return label
    get_state_display.short_description = 'State'


@admin.register(HaLogins)
class HaLoginsAdmin(admin.ModelAdmin):
    list_display = ['user', 'user_id_str', 'login_provider', 'login_provider_identifier', 'created_by_id']
    list_filter = ['login_provider']
    search_fields = ['user_id_str', 'login_provider_identifier', 'login_provider']
    raw_id_fields = ['user']
    ordering = ['-id']
