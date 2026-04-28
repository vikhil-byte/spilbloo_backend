from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("availability", "0002_alter_doctorslot_id_alter_notification_id_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="PrescriptionUpload",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("booking_id", models.IntegerField()),
                ("notes", models.TextField(blank=True, null=True)),
                ("file", models.FileField(blank=True, null=True, upload_to="prescriptions/")),
                ("created_on", models.DateTimeField(auto_now_add=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="prescription_uploads",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "tbl_prescription_upload",
            },
        ),
    ]
