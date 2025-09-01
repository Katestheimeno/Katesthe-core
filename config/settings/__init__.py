"""
Modular settings aggregator. Imports per-concern modules into Django settings.
Path: config/settings/__init__.py
"""

from config.settings.apps_middlewares import *
from config.settings.paths import *
from config.settings.auth import *
from config.settings.lang_time import *
from config.settings.database import *
from config.settings.unfold import *
from config.settings.corsheaders import *
from config.settings.restframework import *
from config.settings.djoser import *
from config.settings.spectacular import *
from config.settings.celery import *
from config.settings.channels import *
