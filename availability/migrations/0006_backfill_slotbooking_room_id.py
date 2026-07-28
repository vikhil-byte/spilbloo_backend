from django.db import migrations


def backfill_room_ids(apps, schema_editor):
    """
    Populate empty room_id for existing bookings using the same scheme the
    clients use: {patient_id}_{doctor_id}_{slot_id}. Without this, join/call
    fails because the Agora channel name is blank.
    """
    SlotBooking = apps.get_model("availability", "SlotBooking")
    for booking in SlotBooking.objects.filter(room_id__in=["", None]):
        booking.room_id = f"{booking.created_by_id}_{booking.doctor_id}_{booking.slot_id}"
        booking.save(update_fields=["room_id"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("availability", "0005_slotbooking_room_id"),
    ]

    operations = [
        migrations.RunPython(backfill_room_ids, noop_reverse),
    ]
