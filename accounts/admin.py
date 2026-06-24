from django.contrib import admin
from django import forms
from .models import User, HaLogins

from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('email',)

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = '__all__'

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    
    list_display = ('id', 'email', 'full_name', 'role_id', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'role_id', 'state_id')
    search_fields = ('email', 'full_name', 'contact_no')
    ordering = ('-date_joined',)
    readonly_fields = ('date_joined', 'last_login')

    # Exposes fields in clean sections, including groups/permissions and superuser checkbox
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'date_of_birth', 'gender', 'contact_no', 'address', 'city', 'country', 'zipcode')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions', 'role_id', 'state_id')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password'),
        }),
    )

@admin.register(HaLogins)
class HaLoginsAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'user_id_str', 'login_provider', 'login_provider_identifier', 'created_by_id')
    list_filter = ('login_provider',)
    search_fields = ('user_id_str', 'login_provider', 'login_provider_identifier')
    ordering = ('-id',)
    
    list_select_related = ('user',)
    raw_id_fields = ('user',)
