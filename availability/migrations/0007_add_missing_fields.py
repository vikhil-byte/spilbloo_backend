from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ("availability", "0006_backfill_slotbooking_room_id"),
    ]

    operations = [
        # --- Notification: remove legacy 'html' column (PHP uses 'description') ---
        migrations.RemoveField(
            model_name="notification",
            name="html",
        ),
        # --- SlotBooking: date, description, call_duration, duration_millisec, old_date ---
        migrations.AddField(
            model_name="slotbooking",
            name="date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="slotbooking",
            name="description",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="slotbooking",
            name="call_duration",
            field=models.CharField(blank=True, default="00:00:00", max_length=16, null=True),
        ),
        migrations.AddField(
            model_name="slotbooking",
            name="duration_millisec",
            field=models.CharField(blank=True, default="", max_length=32, null=True),
        ),
        migrations.AddField(
            model_name="slotbooking",
            name="old_date",
            field=models.DateField(blank=True, null=True),
        ),
        # --- Slot: slot_gap_time, type_id, created_on, created_by ---
        migrations.AddField(
            model_name="slot",
            name="slot_gap_time",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="slot",
            name="type_id",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="slot",
            name="created_on",
            field=models.DateTimeField(auto_now_add=True, blank=True, null=True),
        ),
        migrations.AddField(
            model_name="slot",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="slots",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        # --- DoctorSlot: availability_doctor_id, type_id ---
        migrations.AddField(
            model_name="doctorslot",
            name="availability_doctor_id",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="doctorslot",
            name="type_id",
            field=models.IntegerField(default=0),
        ),
        # --- Notification: description, model_id, state_id, type_id ---
        migrations.AddField(
            model_name="notification",
            name="description",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="notification",
            name="model_id",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="notification",
            name="state_id",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="notification",
            name="type_id",
            field=models.IntegerField(default=0),
        ),
    ]
