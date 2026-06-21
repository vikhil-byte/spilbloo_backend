from django.contrib import admin
from .models import Call

@admin.register(Call)
class CallAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'booking_id', 'session_id', 'duration', 'state_id', 'created_on', 'created_by')
    list_filter = ('state_id', 'created_on')
    search_fields = ('session_id',)
    ordering = ('-created_on',)
    
    # Query optimizations
    list_select_related = ('user', 'created_by')
    raw_id_fields = ('user', 'created_by')
