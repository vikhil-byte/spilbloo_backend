from django.db import migrations, models


def add_state_column_if_missing(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        columns = [
            c.name
            for c in schema_editor.connection.introspection.get_table_description(
                cursor, "tbl_user"
            )
        ]
        if "state" not in columns:
            User = apps.get_model("accounts", "User")
            field = models.CharField(blank=True, max_length=128, null=True)
            field.set_attributes_from_name("state")
            schema_editor.add_field(User, field)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0011_normalize_contact_no_e164"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="user",
                    name="state",
                    field=models.CharField(blank=True, max_length=128, null=True),
                ),
            ],
            database_operations=[
                migrations.RunPython(
                    add_state_column_if_missing,
                    reverse_code=migrations.RunPython.noop,
                ),
            ],
        ),
    ]
