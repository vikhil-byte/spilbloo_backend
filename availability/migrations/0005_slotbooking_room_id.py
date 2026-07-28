from django.db import migrations, models, connection


def _has_column(table, column):
    with connection.cursor() as cursor:
        description = connection.introspection.get_table_description(cursor, table)
    return any(col.name == column for col in description)


def add_columns_if_missing(apps, schema_editor):
    """
    PHP legacy table may already have room_id / is_call_end / complete_reason.
    Only ADD COLUMN when missing so migrate is safe on both fresh and legacy DBs.
    """
    SlotBooking = apps.get_model("availability", "SlotBooking")
    table = SlotBooking._meta.db_table
    with connection.cursor() as cursor:
        if not _has_column(table, "room_id"):
            cursor.execute(
                f"ALTER TABLE {table} ADD COLUMN room_id varchar(255) DEFAULT '' NOT NULL"
            )
        if not _has_column(table, "is_call_end"):
            cursor.execute(
                f"ALTER TABLE {table} ADD COLUMN is_call_end integer DEFAULT 0 NOT NULL"
            )
        if not _has_column(table, "complete_reason"):
            cursor.execute(
                f"ALTER TABLE {table} ADD COLUMN complete_reason varchar(255) NULL"
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
                migrations.AddField(
                    model_name="slotbooking",
                    name="is_call_end",
                    field=models.IntegerField(default=0),
                ),
                migrations.AddField(
                    model_name="slotbooking",
                    name="complete_reason",
                    field=models.CharField(blank=True, max_length=255, null=True),
                ),
            ],
            database_operations=[
                migrations.RunPython(add_columns_if_missing, noop_reverse),
            ],
        ),
    ]
