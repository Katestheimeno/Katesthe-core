"""
Custom validators for the application
"""
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import phonenumbers
from phonenumbers import NumberParseException
VALID_PREFIXES = ("6", "7")


def validate_moroccan_phone_number(value):
    """
    Custom validator for Moroccan phone numbers.
    Strictly accepts only mobile prefixes: 05, 06, 07

    Valid formats:
    - International: +212506363283, +212606363283, +212706363283
    - Local: 0506363283, 0606363283, 0706363283

    Invalid formats (will be rejected):
    - Any prefix other than 5, 6, or 7 (e.g., +212406363283, 0406363283)

    Args:
        value: PhoneNumber object or string

    Raises:
        ValidationError: If the phone number is invalid
    """
    if not value:
        return

    # Convert to string if it's a PhoneNumber object
    # PhoneNumber objects convert to E.164 format (e.g., "+212612345678")
    phone_str = str(value).strip()

    # Remove any spaces or formatting characters for validation
    phone_clean = phone_str.replace(" ", "").replace("-", "").replace(".", "")

    # Check for international format: +212(5|6|7)XXXXXXXX
    if phone_clean.startswith("+212"):
        # Extract the number after +212
        number_part = phone_clean[4:]

        # Must be exactly 9 digits
        if len(number_part) != 9 or not number_part.isdigit():
            raise ValidationError(
                _("Moroccan phone number must have 9 digits after +212 (e.g., +212612345678)")
            )

        # Check if it starts with valid mobile prefix (5, 6, or 7 only)
        first_digit = number_part[0]
        if first_digit not in VALID_PREFIXES:
            raise ValidationError(
                _("Moroccan mobile number must start with 6, or 7 after +212 (e.g., +212612345678)")
            )

        # Valid international format
        return

    # Check for local format: 0(5|6|7)XXXXXXXX
    elif phone_clean.startswith("0"):
        # Extract the number after 0
        number_part = phone_clean[1:]

        # Must be exactly 9 digits
        if len(number_part) != 9 or not number_part.isdigit():
            raise ValidationError(
                _("Moroccan phone number must have 9 digits after 0 (e.g., 0612345678)")
            )

        # Check if it starts with valid mobile prefix (5, 6, or 7 only)
        first_digit = number_part[0]
        if first_digit not in VALID_PREFIXES:
            raise ValidationError(
                _("Moroccan mobile number must start with 6, or 7 after 0 (e.g., 0612345678)")
            )

        # Valid local format - convert to international for storage
        # The PhoneNumberField will handle this conversion
        return

    # If neither format matches, try standard validation as fallback
    try:
        parsed_number = phonenumbers.parse(phone_str, "MA")

        # Check if it's a valid number according to the library
        if phonenumbers.is_valid_number(parsed_number):
            # Additional check: ensure it's a mobile number with prefix 5, 6, or 7
            parsed_str = str(parsed_number.national_number)
            if len(parsed_str) == 9 and parsed_str[0] in VALID_PREFIXES:
                return

        # Standard validation passed but doesn't match our strict rules
        raise ValidationError(
            _("Moroccan mobile number must start with 6, or 7 (e.g., +212612345678 or 0612345678)")
        )

    except NumberParseException:
        raise ValidationError(
            _("Enter a valid Moroccan phone number. Use international format (+212612345678) or local format (0612345678)")
        )
    except ValidationError:
        # Re-raise ValidationError as-is
        raise
    except Exception as e:
        # Catch any other exceptions and provide a helpful error message
        raise ValidationError(
            _("Invalid phone number format. Use international format (+212612345678) or local format (0612345678)")
        )
