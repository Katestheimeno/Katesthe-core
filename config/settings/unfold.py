imports = []

imports += ["UNFOLD"]

UNFOLD = {
    "SITE_TITLE": "DRF Starter Admin",
    "SITE_HEADER": "DRF Starter",
    
    # Base and primary color palettes
    "COLORS": {
        "base": {
            "50": "245 245 245",  # Ice gray
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
        "primary": {
            "50": "235 230 240",  # Light gray-purple
            "100": "210 200 225",
            "200": "180 160 200",
            "300": "145 125 175",
            "400": "115 90 150",   # Balanced brand purple
            "500": "90 60 120",    # Rich dark purple
            "600": "70 45 95",     # Deep
            "700": "55 35 75",
            "800": "40 25 55",
            "900": "25 15 35",
            "950": "10 8 20",
        },
        "accent": {
            "50": "245 250 255",   # Soft blue
            "100": "210 230 250",
            "200": "180 210 245",
            "300": "150 190 240",
            "400": "120 165 230",
            "500": "90 140 220",   # Primary accent
            "600": "65 110 180",
            "700": "45 80 130",
            "800": "25 50 80",
            "900": "15 30 50",
        },
        "success": {
            "500": "40 180 100",
        },
        "warning": {
            "500": "240 180 40",
        },
        "danger": {
            "500": "220 50 50",
        },
    },

    "SIDEBAR": {
        "show_search": True,        # Search for apps/models
        "collapse": False,          # Keep sidebar expanded by default
        "highlight_current": True,  # Highlight the current page
    },

    # Optional UI tweaks
    "UI": {
        # "logo_url": "/static/img/logo.png",  # Your logo
        "dark_mode": True,                   # Default theme
        "rounded_corners": True,              # Smooth card edges
        "compact_tables": True,               # Reduce table row height
    },

    # Footer / extra info
    "FOOTER": {
        "show": True,
        "text": "© 2025 DRF Starter",
    },
}

__all__ = imports

