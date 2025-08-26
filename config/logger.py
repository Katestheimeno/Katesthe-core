# config/logger.py
import logging
from loguru import logger
import sys
from pathlib import Path
import os
import socket

# ------------------------------------------------------------
# Setup directories
# ------------------------------------------------------------
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# ------------------------------------------------------------
# Helper: environment-based log level
# ------------------------------------------------------------
ENV = os.getenv("DJANGO_ENV", "local").lower()
CONSOLE_LEVEL = "DEBUG" if ENV in ("local", "dev") else "INFO"
FILE_LEVEL = "DEBUG"

# ------------------------------------------------------------
# Remove default Loguru logger
# ------------------------------------------------------------
logger.remove()

# ------------------------------------------------------------
# Format strings
# ------------------------------------------------------------
console_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level>\n"
    "<cyan>Module:</cyan> {name} | <cyan>Function:</cyan> {function} | <cyan>Line:</cyan> {line}\n"
    "<magenta>Thread:</magenta> {thread.name} | <magenta>Process:</magenta> {process.name}\n"
    "<level>{message}</level>\n"
    "------------------------------------------------------------"
)

file_format = (
    "{time:YYYY-MM-DD HH:mm:ss} | {level: <8}\n"
    "Module: {name} | Function: {function} | Line: {line}\n"
    "Process: {process.name} | Thread: {thread.name}\n"
    "{message}\n"
    "------------------------------------------------------------"
)
# ------------------------------------------------------------
# Console sink
# ------------------------------------------------------------
logger.add(
    sys.stdout,
    level=CONSOLE_LEVEL,
    format=console_format,
    colorize=True,
    backtrace=True,
    diagnose=True
)

# ------------------------------------------------------------
# File sinks per level
# ------------------------------------------------------------
levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
for level_name in levels:
    logger.add(
        LOG_DIR / f"{level_name.lower()}_{{time:YYYY-MM-DD}}.log",
        level=level_name,
        format=file_format,
        rotation="10 MB",
        retention="14 days",
        compression="zip",
        encoding="utf-8",
        enqueue=True,
        backtrace=True,
        diagnose=True
    )

# ------------------------------------------------------------
# Optional: Add hostname or process info as extra context
# ------------------------------------------------------------
HOSTNAME = socket.gethostname()
logger = logger.bind(host=HOSTNAME, env=ENV)

# ------------------------------------------------------------
# Intercept Django logs
# ------------------------------------------------------------


class InterceptHandler(logging.Handler):
    """Redirect all logs from Python logging (Django, libraries) to Loguru"""

    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        logger.opt(depth=6, exception=record.exc_info).log(
            level, record.getMessage())


def setup_django_logging():
    """Call early in settings/base.py to capture all Django logs"""
    logging.root.handlers = []
    logging.basicConfig(handlers=[InterceptHandler()], level=0)

    django_loggers = [
        "django",
        "django.server",
        "django.db.backends",
        "py.warnings",
    ]
    for name in django_loggers:
        logging.getLogger(name).handlers = [InterceptHandler()]
        logging.getLogger(name).propagate = False
