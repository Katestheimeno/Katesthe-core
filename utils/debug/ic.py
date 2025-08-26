"""
Custom IceCream setup and helper timer for debug printing.
Path: utils/debug/ic.py
"""

from contextlib import contextmanager
from django.conf import settings as cfg
import time
from icecream import ic
from pprint import pformat

# === Debugging Utilities with IceCream ===
# This module customizes IceCream (ic) for styled, structured debug output.
# Features:
#   - Colored, styled console output for better readability
#   - Context info (file, line, function) in debug prints
#   - Pretty-printing for nested dicts/lists using pprint
#   - Timer context manager for quick performance checks
#   - Auto-disable ic when DEBUG=False (keeps production logs clean)

# ANSI escape codes for styling output
RESET = "\033[0m"
BOLD = "\033[1m"
UNDERLINE = "\033[4m"
BLUE = "\033[94m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
GREY = "\033[90m"


def styled_output(s: str) -> None:
    """Custom printer for ic output with colors & framing."""
    print(f"""
{CYAN}{'='*100}
{BOLD}📦 IC DEBUG OUTPUT{RESET}
{YELLOW}{s}{RESET}
{CYAN}{'='*100}{RESET}\n
""")


# Configure IceCream behavior
ic.configureOutput(
    includeContext=True,          # show file, line, func name
    prefix=f"{MAGENTA}→ {RESET}",  # colored prefix before output
    outputFunction=styled_output,  # use our custom pretty printer
    contextAbsPath=True,          # show absolute paths in context
)

# Use pprint for cleaner formatting of dicts/lists/sets
ic.formatter = lambda s: pformat(s, indent=2, width=100)


@contextmanager
def ic_timer(label: str = ""):
    """
    Context manager to measure execution time of code blocks.
    Example:
        with ic_timer("Expensive query"):
            queryset = MyModel.objects.all()
    """
    start = time.time()
    yield
    duration = time.time() - start
    ic(f"{label} took {duration:.4f}s")


# Disable ic in production to avoid leaking debug info
if not cfg.DEBUG:
    ic.disable()
