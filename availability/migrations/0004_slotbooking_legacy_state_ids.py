from django.db import migrations, models, connection


def _has_column(table, column):
    with connection.cursor() as cursor:
        description = connection.introspection.get_table_description(cursor, table)
    return any(col.name == column for col in description)


def remap_django_booking_states(apps, schema_editor):
    """
    Map incorrect Django SlotBooking states onto legacy PHP / iOS values.

    Wrong Django scheme: REQUEST=2, ACCEPT=3, CANCELED=4, COMPLETED=5
    Legacy PHP/iOS:      REQUEST=0, ACCEPT=1, CANCELED=2, COMPLETED=3

    Order matters so remapped completed/canceled rows are not reclassified.
    Ambiguous 2/3 rows (could be PHP canceled/completed) are only remapped
    when they still look like open Django request/accept bookings.
    """
    SlotBooking = apps.get_model("availability", "SlotBooking")
    table = SlotBooking._meta.db_table
    has_is_call_end = _has_column(table, "is_call_end")
    has_complete_reason = _has_column(table, "complete_reason")

    with connection.cursor() as cursor:
        # 1) Django ACCEPT(3) → PHP ACCEPT(1); leave real completions alone.
        accept_sql = f"""
            UPDATE {table}
            SET state_id = 1
            WHERE state_id = 3
              AND (cancel_reason IS NULL OR cancel_reason = '')
        """
        if has_is_call_end:
            accept_sql += " AND (is_call_end IS NULL OR is_call_end = 0)"
        if has_complete_reason:
            accept_sql += " AND (complete_reason IS NULL OR complete_reason = '')"
        cursor.execute(accept_sql)

        # 2) Django REQUEST(2) → PHP REQUEST(0); leave PHP canceled(2) alone.
        cursor.execute(
            f"""
            UPDATE {table}
            SET state_id = 0
            WHERE state_id = 2
              AND (cancel_reason IS NULL OR cancel_reason = '')
              AND (is_refunded IS NULL OR is_refunded = 0)
            """
        )

        # 3) Unambiguous Django-only values.
        cursor.execute(f"UPDATE {table} SET state_id = 3 WHERE state_id = 5")
        cursor.execute(f"UPDATE {table} SET state_id = 2 WHERE state_id = 4")


def noop_reverse(apps, schema_editor):
    # Irreversible without knowing which rows were PHP vs Django originally.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("availability", "0003_prescriptionupload"),
    ]

    operations = [
        migrations.AlterField(
            model_name="slotbooking",
            name="state_id",
            field=models.IntegerField(
                choices=[
                    (0, "Request"),
                    (1, "Accept"),
                    (2, "Canceled"),
                    (3, "Completed"),
                ],
                default=0,
            ),
        ),
        migrations.RunPython(remap_django_booking_states, noop_reverse),
    ]
