from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("calls", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="call",
            name="call_end_id",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="call",
            name="token",
            field=models.CharField(blank=True, max_length=512, null=True),
        ),
        migrations.AddField(
            model_name="call",
            name="type_id",
            field=models.IntegerField(default=0),
        ),
    ]
