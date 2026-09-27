"""
Data migration: Normalize all existing contact_no values to E.164 format.

e.g. "919876543210" → "+919876543210"
     "9876543210"   → "+919876543210"
     "+919876543210" → no change
"""
import logging
from django.db import migrations

logger = logging.getLogger(__name__)


def normalize_contact_nos_to_e164(apps, schema_editor):
    """Normalize all existing contact_no values to E.164 format using phonenumbers."""
    try:
        import phonenumbers
    except ImportError:
        logger.error("phonenumbers library not installed — skipping contact_no migration")
        return

    User = apps.get_model("accounts", "User")
    users = User.objects.exclude(contact_no__isnull=True).exclude(contact_no="")
    updated = 0
    skipped = 0

    for user in users.iterator(chunk_size=500):
        original = user.contact_no
        if not original or not original.strip():
            continue

        raw = original.strip()

        # Already in E.164 format
        if raw.startswith("+"):
            try:
                parsed = phonenumbers.parse(raw, None)
                if phonenumbers.is_valid_number(parsed):
                    e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
                    if e164 != raw:
                        user.contact_no = e164
                        user.save(update_fields=["contact_no"])
                        updated += 1
                    continue
            except phonenumbers.NumberParseException:
                pass

        # Try parsing with country_code hint from the user record
        country_hint = "IN"
        if user.country_code:
            import re
            cc_digits = re.sub(r"\D", "", str(user.country_code))
            dial_map = {"91": "IN", "1": "US", "44": "GB", "61": "AU", "971": "AE", "966": "SA", "65": "SG"}
            country_hint = dial_map.get(cc_digits, "IN")

        # Try as-is with country hint
        try:
            parsed = phonenumbers.parse(raw, country_hint)
            if phonenumbers.is_valid_number(parsed):
                e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
                user.contact_no = e164
                user.save(update_fields=["contact_no"])
                updated += 1
                continue
        except phonenumbers.NumberParseException:
            pass

        # Try prepending '+'
        try:
            parsed = phonenumbers.parse(f"+{raw}", None)
            if phonenumbers.is_valid_number(parsed):
                e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
                user.contact_no = e164
                user.save(update_fields=["contact_no"])
                updated += 1
                continue
        except phonenumbers.NumberParseException:
            pass

        logger.warning("Could not normalize contact_no='%s' for user id=%s — skipping", original, user.id)
        skipped += 1

    logger.info("E.164 migration complete: %d updated, %d skipped", updated, skipped)


def reverse_noop(apps, schema_editor):
    """No reverse — E.164 is the canonical format going forward."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0010_user_country_code"),
    ]

    operations = [
        migrations.RunPython(
            normalize_contact_nos_to_e164,
            reverse_code=reverse_noop,
        ),
    ]
