# Generated for CompanyCouponUser model (tbl_company_coupon_user)

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('company', '0001_initial'),
        ('plans', '0008_add_missing_plan_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CompanyCouponUser',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('coupon_code', models.CharField(max_length=255)),
                ('state_id', models.SmallIntegerField(choices=[(0, 'New'), (1, 'Active'), (2, 'Deleted')], default=1)),
                ('type_id', models.IntegerField(default=0)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('coupon', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='coupon_users', to='company.companycoupon')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='coupon_users', to='company.company')),
                ('plan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='company_coupon_users', to='plans.plan')),
                ('subscribed_plan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='company_coupon_users', to='plans.subscribedplan')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='company_coupon_users_created', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'tbl_company_coupon_user',
            },
        ),
    ]
