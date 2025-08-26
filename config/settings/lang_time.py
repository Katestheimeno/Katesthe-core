"""
Language, timezone, and i18n/l10n settings.
Path: config/settings/lang_time.py
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
