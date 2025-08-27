"""
Unfold Admin UI configuration.
Path: config/settings/unfold.py
"""

from config.env import PROJECT_NAME, THEME_PRIMARY_COLOR, THEME_ACCENT_COLOR

# ------------------------------------------------------------
# Helper function to convert hex to RGB
# ------------------------------------------------------------
def hex_to_rgb(hex_color):
    """Convert hex color to RGB format for Unfold."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

# Convert theme colors to RGB
primary_rgb = hex_to_rgb(THEME_PRIMARY_COLOR)
accent_rgb = hex_to_rgb(THEME_ACCENT_COLOR)

# ------------------------------------------------------------
# Imports Collector
# ------------------------------------------------------------
imports = []


# ------------------------------------------------------------
# Unfold Configuration
# ------------------------------------------------------------
imports += ["UNFOLD"]

UNFOLD = {
    # --------------------------------------------------------
    # Branding
    # --------------------------------------------------------
    "SITE_TITLE": f"{PROJECT_NAME} Admin",  # Browser tab + login screen
    "SITE_HEADER": PROJECT_NAME,       # Header displayed in the admin

    # --------------------------------------------------------
    # Color Palette
    # Uses RGB values (e.g., "90 60 120") for consistency.
    # Tailored for a professional purple/gray/blue theme.
    # --------------------------------------------------------
    "COLORS": {
        "base": {   # Neutral grays
            "50": "245 245 245",   # Ice gray
            "100": "225 225 225",
            "200": "190 190 190",
            "300": "150 150 150",
            "400": "110 110 110",
            "500": "80 80 80",
            "600": "50 50 50",
            "700": "30 30 30",
            "800": "15 15 15",
            "900": "8 8 8",
            "950": "2 2 2",
        },
        "primary": {  # Main branding color (configurable)
            "50": f"{primary_rgb[0] + 145} {primary_rgb[1] + 170} {primary_rgb[2] + 240}",
            "100": f"{primary_rgb[0] + 120} {primary_rgb[1] + 140} {primary_rgb[2] + 225}",
            "200": f"{primary_rgb[0] + 90} {primary_rgb[1] + 100} {primary_rgb[2] + 200}",
            "300": f"{primary_rgb[0] + 55} {primary_rgb[1] + 65} {primary_rgb[2] + 175}",
            "400": f"{primary_rgb[0] + 25} {primary_rgb[1] + 30} {primary_rgb[2] + 150}",
            "500": f"{primary_rgb[0]} {primary_rgb[1]} {primary_rgb[2]}",    # Main color
            "600": f"{max(0, primary_rgb[0] - 20)} {max(0, primary_rgb[1] - 15)} {max(0, primary_rgb[2] - 25)}",
            "700": f"{max(0, primary_rgb[0] - 35)} {max(0, primary_rgb[1] - 25)} {max(0, primary_rgb[2] - 45)}",
            "800": f"{max(0, primary_rgb[0] - 50)} {max(0, primary_rgb[1] - 35)} {max(0, primary_rgb[2] - 65)}",
            "900": f"{max(0, primary_rgb[0] - 65)} {max(0, primary_rgb[1] - 45)} {max(0, primary_rgb[2] - 85)}",
            "950": f"{max(0, primary_rgb[0] - 80)} {max(0, primary_rgb[1] - 52)} {max(0, primary_rgb[2] - 100)}",
        },
        "accent": {  # Highlights / secondary actions (configurable)
            "50": f"{accent_rgb[0] + 155} {accent_rgb[1] + 210} {accent_rgb[2] + 255}",
            "100": f"{accent_rgb[0] + 120} {accent_rgb[1] + 190} {accent_rgb[2] + 250}",
            "200": f"{accent_rgb[0] + 90} {accent_rgb[1] + 170} {accent_rgb[2] + 245}",
            "300": f"{accent_rgb[0] + 60} {accent_rgb[1] + 150} {accent_rgb[2] + 240}",
            "400": f"{accent_rgb[0] + 30} {accent_rgb[1] + 125} {accent_rgb[2] + 230}",
            "500": f"{accent_rgb[0]} {accent_rgb[1]} {accent_rgb[2]}",   # Main accent color
            "600": f"{max(0, accent_rgb[0] - 25)} {max(0, accent_rgb[1] - 30)} {max(0, accent_rgb[2] - 40)}",
            "700": f"{max(0, accent_rgb[0] - 45)} {max(0, accent_rgb[1] - 60)} {max(0, accent_rgb[2] - 90)}",
            "800": f"{max(0, accent_rgb[0] - 65)} {max(0, accent_rgb[1] - 90)} {max(0, accent_rgb[2] - 140)}",
            "900": f"{max(0, accent_rgb[0] - 85)} {max(0, accent_rgb[1] - 120)} {max(0, accent_rgb[2] - 190)}",
        },
        "success": {"500": "40 180 100"},   # Green
        "warning": {"500": "240 180 40"},   # Yellow/Orange
        "danger": {"500": "220 50 50"},     # Red
    },

    # --------------------------------------------------------
    # Sidebar Navigation
    # --------------------------------------------------------
    "SIDEBAR": {
        "show_search": True,        # Allow search for apps/models
        "collapse": False,          # Sidebar expanded by default
        "highlight_current": True,  # Highlight the active menu item
    },

    # --------------------------------------------------------
    # User Interface Tweaks
    # --------------------------------------------------------
    "UI": {
        # "logo_url": "/static/img/logo.png",  # Optional custom logo
        "dark_mode": True,                    # Default dark theme
        "rounded_corners": True,              # Smooth card edges
        "compact_tables": True,               # Smaller row height for tables
    },

    # --------------------------------------------------------
    # Footer
    # --------------------------------------------------------
    "FOOTER": {
        "show": True,
        "text": f"© 2025 {PROJECT_NAME}",
    },
}


# ------------------------------------------------------------
# Explicit Exports
# ------------------------------------------------------------
__all__ = imports
