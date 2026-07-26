from django.db import migrations, models, connection


def _has_column(table, column):
    with connection.cursor() as cursor:
        description = connection.introspection.get_table_description(cursor, table)
    return any(col.name == column for col in description)


def add_room_id_if_missing(apps, schema_editor):
    """PHP legacy table may already have room_id; only add when missing."""
    SlotBooking = apps.get_model("availability", "SlotBooking")
    table = SlotBooking._meta.db_table
    if _has_column(table, "room_id"):
        return
    with connection.cursor() as cursor:
        cursor.execute(
            f"ALTER TABLE {table} ADD COLUMN room_id varchar(255) DEFAULT '' NOT NULL"
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("availability", "0004_slotbooking_legacy_state_ids"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="slotbooking",
                    name="room_id",
                    field=models.CharField(blank=True, default="", max_length=255),
                ),
            ],
            database_operations=[
                migrations.RunPython(add_room_id_if_missing, noop_reverse),
            ],
        ),
    ]
