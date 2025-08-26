"""
Authentication and password validation settings.
Path: config/settings/auth.py
"""

imports = []

# ---------------------------------------------------------------------
# Password Validators
# ---------------------------------------------------------------------
# The AUTH_PASSWORD_VALIDATORS setting is a list of dictionaries where
# each entry specifies a validator class to use.
#
# Validators included here:
#
# 1. UserAttributeSimilarityValidator
#    Prevents passwords that are too similar to the user's personal
#    information (username, email, etc).
#
# 2. MinimumLengthValidator
#    Ensures that the password has a minimum length (default: 8 chars).
#    You can customize the minimum length by passing an "OPTIONS" dict.
#
# 3. CommonPasswordValidator
#    Prevents use of common, easily guessable passwords
#    (e.g., "password123", "qwerty").
#
# 4. NumericPasswordValidator
#    Disallows passwords that consist entirely of numbers.
#
# You can extend or override these by adding custom validators or
# changing the configuration of the existing ones.
# ---------------------------------------------------------------------
imports += ["AUTH_PASSWORD_VALIDATORS"]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        # "OPTIONS": {"min_length": 10},  # Example of customization
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Point django to the custom user model
imports += ["AUTH_USER_MODEL"]
AUTH_USER_MODEL = "accounts.User"

# Expose only the explicitly defined symbols
__all__ = imports
