"""
Django settings for profiling with PyInstrument.

This settings file enables PyInstrument profiling middleware
to capture performance data for the application.
"""

from .base import *
from config.logger import logger

# ------------------------------------------------------------
# PyInstrument Profiling Configuration
# ------------------------------------------------------------

# Add PyInstrument middleware at the top of the middleware stack
MIDDLEWARE = [
    'pyinstrument.middleware.ProfilerMiddleware',
] + MIDDLEWARE

# PyInstrument settings
PYINSTRUMENT_PROFILE_DIR = BASE_DIR / 'profiles'
PYINSTRUMENT_PROFILE_DIR.mkdir(exist_ok=True)

# Configure PyInstrument
PYINSTRUMENT = {
    'PROFILE_DIR': str(PYINSTRUMENT_PROFILE_DIR),
    'SHOW_CALLBACK': lambda request: True,  # Always profile
    'SHOW_PYINSTRUMENT': True,  # Show PyInstrument toolbar
    'PYINSTRUMENT_USE_SIGNAL': False,  # Use middleware instead of signal
    'PYINSTRUMENT_SHOW_CALLBACK': lambda request: True,  # Always show for profiling mode
}

# Additional profiling settings
PROFILING_ENABLED = True

# Log profiling information using loguru
logger.info("🔍 PyInstrument profiling mode enabled")
logger.info(f"📊 Profile output directory: {PYINSTRUMENT_PROFILE_DIR}")

# Override DEBUG to True for profiling (if not already)
DEBUG = True

# Enable development apps and profiling apps
if DEBUG:
    INSTALLED_APPS += DEV_APPS + PROFILING_APPS
    MIDDLEWARE += [
        'silk.middleware.SilkyMiddleware',
    ]

    ROSETTA_MESSAGES_PER_PAGE = 100
    ROSETTA_SHOW_ATTEMPTS = True
    ROSETTA_REQUIRES_AUTH = True
