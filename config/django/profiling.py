"""
Django settings for profiling with PyInstrument.

This settings file enables PyInstrument profiling middleware
to capture performance data for the application.
"""

import os
from .base import *
from config.logger import logger

# ------------------------------------------------------------
# PyInstrument Profiling Configuration
# ------------------------------------------------------------

# PyInstrument settings from environment variables
PYINSTRUMENT_PROFILE_DIR_NAME = os.getenv('PYINSTRUMENT_PROFILE_DIR', 'profiles')
PYINSTRUMENT_PROFILE_DIR = BASE_DIR / PYINSTRUMENT_PROFILE_DIR_NAME
PYINSTRUMENT_PROFILE_DIR.mkdir(exist_ok=True)

# Configure PyInstrument behavior from environment
PYINSTRUMENT_ALWAYS_PROFILE = os.getenv('PYINSTRUMENT_ALWAYS_PROFILE', 'True').lower() == 'true'
PYINSTRUMENT_SHOW_TOOLBAR = os.getenv('PYINSTRUMENT_SHOW_TOOLBAR', 'True').lower() == 'true'
PYINSTRUMENT_USE_SIGNAL = os.getenv('PYINSTRUMENT_USE_SIGNAL', 'False').lower() == 'true'

# Add PyInstrument middleware at the top of the middleware stack
MIDDLEWARE = [
    'pyinstrument.middleware.ProfilerMiddleware',
] + MIDDLEWARE

# Configure PyInstrument
PYINSTRUMENT = {
    'PROFILE_DIR': str(PYINSTRUMENT_PROFILE_DIR),
    'SHOW_CALLBACK': lambda request: PYINSTRUMENT_ALWAYS_PROFILE,
    'SHOW_PYINSTRUMENT': PYINSTRUMENT_SHOW_TOOLBAR,
    'PYINSTRUMENT_USE_SIGNAL': PYINSTRUMENT_USE_SIGNAL,
    'PYINSTRUMENT_SHOW_CALLBACK': lambda request: PYINSTRUMENT_ALWAYS_PROFILE,
}

# Additional profiling settings
PROFILING_ENABLED = os.getenv('PROFILING_ENABLED', 'True').lower() == 'true'

# Log profiling information using loguru
logger.info("🔍 PyInstrument profiling mode enabled")
logger.info(f"📊 Profile output directory: {PYINSTRUMENT_PROFILE_DIR}")
logger.info(f"🎯 Always profile: {PYINSTRUMENT_ALWAYS_PROFILE}")
logger.info(f"🔧 Show toolbar: {PYINSTRUMENT_SHOW_TOOLBAR}")

# Override DEBUG to True for profiling (if not already)
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

# Enable development apps and profiling apps
if DEBUG:
    INSTALLED_APPS += DEV_APPS + PROFILING_APPS
    MIDDLEWARE += [
        'silk.middleware.SilkyMiddleware',
    ]

    ROSETTA_MESSAGES_PER_PAGE = 100
    ROSETTA_SHOW_ATTEMPTS = True
    ROSETTA_REQUIRES_AUTH = True
