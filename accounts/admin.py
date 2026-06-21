from django.contrib import admin
from .models import User, HaLogins

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'full_name', 'role_id', 'is_active', 'is_staff', 'date_joined')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'role_id', 'state_id')
    search_fields = ('email', 'full_name', 'contact_no')
    ordering = ('-date_joined',)
    readonly_fields = ('date_joined', 'last_login')

@admin.register(HaLogins)
class HaLoginsAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'user_id_str', 'login_provider', 'login_provider_identifier', 'created_by_id')
    list_filter = ('login_provider',)
    search_fields = ('user_id_str', 'login_provider', 'login_provider_identifier')
    ordering = ('-id',)
    
    list_select_related = ('user',)
    raw_id_fields = ('user',)
