from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0020_therapistapplication_rci_file"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="nodesubscriptionplan",
            options={"managed": False},
        ),
    ]
