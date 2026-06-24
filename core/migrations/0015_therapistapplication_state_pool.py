from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_create_missing_tables'),
    ]

    operations = [
        migrations.AlterField(
            model_name='therapistapplication',
            name='state_id',
            field=models.SmallIntegerField(
                choices=[
                    (0, 'New'),
                    (1, 'Accept'),
                    (2, 'Reject'),
                    (3, 'Added'),
                    (4, 'Pool'),
                ],
                default=0,
            ),
        ),
    ]
