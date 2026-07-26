from rest_framework import serializers
from rest_framework.views import APIView
from .models import DoctorSlot, SlotBooking, Slot, Notification

class SlotSerializer(serializers.ModelSerializer):
    is_selected = serializers.SerializerMethodField()

    class Meta:
        model = Slot
        fields = ('id', 'start_time', 'end_time', 'is_selected')

    def get_is_selected(self, obj):
        request = self.context.get('request')
        start_time = self.context.get('start_time')
        end_time = self.context.get('end_time')
        if start_time and end_time and request and request.user and request.user.is_authenticated:
            return DoctorSlot.objects.filter(
                created_by=request.user,
                availability_slot_id=obj.id,
                start_time__gte=start_time,
                start_time__lte=end_time,
            ).exists()
        return False

class DoctorSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorSlot
        fields = '__all__'
        read_only_fields = ('created_by', 'created_on')

def _fmt_val_dt(dt_val, fmt="%Y-%m-%d %H:%M:%S"):
    if not dt_val:
        return ""
    if isinstance(dt_val, str):
        try:
            from dateutil.parser import parse
            dt_val = parse(dt_val)
        except Exception:
            return dt_val
    try:
        return dt_val.strftime(fmt)
    except Exception:
        return str(dt_val)


class SlotBookingSerializer(serializers.ModelSerializer):
    doctor_name = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    start_time = serializers.SerializerMethodField()
    end_time = serializers.SerializerMethodField()
    created_on = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    is_call_end = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    room_id = serializers.SerializerMethodField()
    call_duration = serializers.SerializerMethodField()
    duration_millisec = serializers.SerializerMethodField()
    createdBy = serializers.SerializerMethodField()

    class Meta:
        model = SlotBooking
        fields = (
            'id', 'date', 'doctor_id', 'doctor_name', 'slot_id',
            'start_time', 'end_time', 'description', 'room_id',
            'is_active', 'is_call_end', 'state_id', 'type_id',
            'created_on', 'created_by_id', 'patient_name',
            'call_duration', 'duration_millisec', 'patient_reschedule',
            'doctor_reschedule', 'is_reschedule_confirm', 'createdBy',
        )

    def get_date(self, obj):
        return _fmt_val_dt(obj.start_time, "%Y-%m-%d")

    def get_start_time(self, obj):
        return _fmt_val_dt(obj.start_time, "%Y-%m-%d %H:%M:%S")

    def get_end_time(self, obj):
        return _fmt_val_dt(obj.end_time, "%Y-%m-%d %H:%M:%S")

    def get_created_on(self, obj):
        return _fmt_val_dt(obj.created_on, "%Y-%m-%d %H:%M:%S")


    def get_doctor_name(self, obj):
        from accounts.models import User
        doc = User.objects.filter(id=obj.doctor_id).first()
        return doc.first_name if doc else ""

    def get_patient_name(self, obj):
        return obj.created_by.full_name if (obj.created_by and obj.created_by.full_name) else ""

    def get_is_active(self, obj):
        return getattr(obj, "is_active", 0) == 1

    def get_is_call_end(self, obj):
        return False

    def get_description(self, obj):
        return getattr(obj, "description", "") or ""

    def get_room_id(self, obj):
        return getattr(obj, "room_id", "") or ""

    def get_call_duration(self, obj):
        return getattr(obj, "call_duration", "00:00:00") or "00:00:00"

    def get_duration_millisec(self, obj):
        return ""

    def get_createdBy(self, obj):
        user = obj.created_by
        return {
            "video_credits": getattr(user, "video_credit", 0) or 0,
            "no_of_video_session": 0,
        }

