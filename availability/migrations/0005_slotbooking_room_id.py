from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("availability", "0004_slotbooking_legacy_state_ids"),
    ]

    operations = [
        migrations.AddField(
            model_name="slotbooking",
            name="room_id",
            field=models.CharField(max_length=255, blank=True, default=""),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name="slotbooking",
            name="is_call_end",
            field=models.IntegerField(default=0),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name="slotbooking",
            name="complete_reason",
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
    ]
