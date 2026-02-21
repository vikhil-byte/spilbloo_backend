from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL

class Call(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='calls_received', null=True, blank=True)
    booking_id = models.IntegerField(null=True, blank=True)
    session_id = models.CharField(max_length=255, null=True, blank=True) # room_id equivalent
    state_id = models.IntegerField(default=1) # 1=Join, 2=Left, 3=Completed
    
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    duration = models.IntegerField(default=0)
    duration_millisec = models.BigIntegerField(default=0)
    
    created_on = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='calls_created')

    class Meta:
        db_table = 'tbl_call'
