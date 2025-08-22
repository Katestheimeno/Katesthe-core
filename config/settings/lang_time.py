"""
Time & Language Settings

This file serves as a self-contained configuration for internationalization (i18n) 
and localization (l10n) in the Django project.

- LANGUAGE_CODE: Defines the default language for the project.
- TIME_ZONE: Sets the default timezone.
- USE_I18N: Enables Django’s internationalization system (translation, locale).
- USE_TZ: Enables timezone-aware datetimes (recommended for most projects).
"""

# ------------------------------------------------------------
# Imports Collector
# ------------------------------------------------------------
imports = []


# ------------------------------------------------------------
# Language & Timezone
# ------------------------------------------------------------
# Default language for the project.
imports += ["LANGUAGE_CODE"]
LANGUAGE_CODE = "en-us"

# Default timezone for the project.
# TIP: Switch to your preferred timezone, e.g., "Europe/Paris" or "Africa/Casablanca".
imports += ["TIME_ZONE"]
TIME_ZONE = "UTC"

# Enable Django’s translation system (useful if supporting multiple languages).
imports += ["USE_I18N"]
USE_I18N = True

# Enable timezone-aware datetimes.
# Recommended to keep True for correctness across regions.
imports += ["USE_TZ"]
USE_TZ = True


# ------------------------------------------------------------
# Explicit Exports
# ------------------------------------------------------------
__all__ = imports
