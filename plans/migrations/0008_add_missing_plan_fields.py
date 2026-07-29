from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ("plans", "0007_alter_plan_plan_type_alter_subscribedplan_plan_type_and_more"),
    ]

    operations = [
        # --- Plan: weekly_price, image_file, tax_percentage ---
        migrations.AddField(
            model_name="plan",
            name="weekly_price",
            field=models.CharField(default="0", max_length=16),
        ),
        migrations.AddField(
            model_name="plan",
            name="image_file",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="plan",
            name="tax_percentage",
            field=models.CharField(blank=True, max_length=16, null=True),
        ),
        # --- SubscribedPlan: missing PHP columns ---
        migrations.AddField(
            model_name="subscribedplan",
            name="no_of_video_session",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="subscribedplan",
            name="is_doctor_changed",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="subscribedplan",
            name="doctor_price",
            field=models.CharField(blank=True, max_length=16, null=True),
        ),
        migrations.AddField(
            model_name="subscribedplan",
            name="company_coupon_type",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="subscribedplan",
            name="upcoming_plan_video_credit",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="subscribedplan",
            name="incentive_days",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="subscribedplan",
            name="value",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="subscribedplan",
            name="rezorpay_start_time",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="subscribedplan",
            name="start_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="subscribedplan",
            name="end_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="subscribedplan",
            name="trail_end_time",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="subscribedplan",
            name="signature",
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
        migrations.AddField(
            model_name="subscribedplan",
            name="zipcode",
            field=models.CharField(blank=True, max_length=16, null=True),
        ),
        # --- Coupon: description, created_on, created_by ---
        migrations.AddField(
            model_name="coupon",
            name="description",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="coupon",
            name="created_on",
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AddField(
            model_name="coupon",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="coupons",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        # --- WebhookLog: fix db_table + add type_id ---
        migrations.AlterModelTable(
            name="webhooklog",
            table="tbl_subscription_event_log",
        ),
        migrations.AddField(
            model_name="webhooklog",
            name="type_id",
            field=models.IntegerField(default=0),
        ),
    ]
