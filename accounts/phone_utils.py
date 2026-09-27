"""
Canonical phone number normalization using Google's phonenumbers library.

All phone numbers in the system are stored in E.164 format: +919876543210
This module is the single source of truth for parsing and formatting phone numbers.
"""
import phonenumbers
import re
import logging

logger = logging.getLogger(__name__)

# Map common dial-code strings to ISO 3166-1 alpha-2 codes.
# phonenumbers.parse() needs an ISO region code, not a dial code.
_DIAL_CODE_TO_REGION = {
    "91": "IN",
    "1": "US",
    "44": "GB",
    "61": "AU",
    "971": "AE",
    "966": "SA",
    "65": "SG",
    "60": "MY",
    "977": "NP",
    "880": "BD",
    "94": "LK",
    "92": "PK",
}


def resolve_country_hint(raw_country_code=None, default="IN") -> str:
    """
    Convert a raw country_code from the API request into an ISO region code.

    Accepts: "+91", "91", "IN", "+1", "1", "US", etc.
    Returns: "IN", "US", "GB", etc.
    """
    if not raw_country_code:
        return default

    cc = str(raw_country_code).strip().upper()

    # Already an ISO code (e.g. "IN", "US")
    if len(cc) == 2 and cc.isalpha():
        return cc

    # Strip non-digits to get dial code ("+91" → "91")
    digits = re.sub(r"\D", "", cc)
    if not digits:
        return default

    # Try longest match first (3-digit codes like 971, then 2-digit, then 1-digit)
    for length in (3, 2, 1):
        prefix = digits[:length]
        if prefix in _DIAL_CODE_TO_REGION:
            return _DIAL_CODE_TO_REGION[prefix]

    return default


def normalize_phone_e164(raw_phone, country_hint="IN") -> str | None:
    """
    Parse any phone input into E.164 format.

    Returns "+919876543210" or None if the number is invalid.

    Examples:
        normalize_phone_e164("9876543210")           → "+919876543210"
        normalize_phone_e164("9187299381", "IN")      → "+919187299381"
        normalize_phone_e164("919187299381")          → "+919187299381"
        normalize_phone_e164("+919876543210")         → "+919876543210"
        normalize_phone_e164("4155552671", "US")      → "+14155552671"
        normalize_phone_e164("", "IN")                → None
    """
    if not raw_phone:
        return None

    raw = str(raw_phone).strip()
    if not raw:
        return None

    try:
        # If the number already starts with '+', parse as-is (international format)
        if raw.startswith("+"):
            parsed = phonenumbers.parse(raw, None)
        else:
            parsed = phonenumbers.parse(raw, country_hint)

        if not phonenumbers.is_valid_number(parsed):
            # Fallback: try prepending '+' in case it's full digits like "919876543210"
            if not raw.startswith("+"):
                try:
                    parsed_intl = phonenumbers.parse(f"+{raw}", None)
                    if phonenumbers.is_valid_number(parsed_intl):
                        return phonenumbers.format_number(
                            parsed_intl, phonenumbers.PhoneNumberFormat.E164
                        )
                except phonenumbers.NumberParseException:
                    pass
            logger.warning("Invalid phone number: '%s' (hint=%s)", raw_phone, country_hint)
            return None

        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)

    except phonenumbers.NumberParseException as e:
        logger.warning("Failed to parse phone number '%s': %s", raw_phone, e)
        return None


def extract_country_code(raw_phone, country_hint="IN") -> str:
    """
    Extract the display country code (e.g. "+91") from a phone number.

    Returns the formatted dial code or "+91" as default.
    """
    if not raw_phone:
        return "+91"

    raw = str(raw_phone).strip()
    try:
        if raw.startswith("+"):
            parsed = phonenumbers.parse(raw, None)
        else:
            parsed = phonenumbers.parse(raw, country_hint)
        return f"+{parsed.country_code}"
    except phonenumbers.NumberParseException:
        return "+91"
