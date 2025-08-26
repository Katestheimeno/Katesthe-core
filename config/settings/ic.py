from icecream import ic

# ANSI escape codes for colors
RESET = "\033[0m"
BOLD = "\033[1m"
UNDERLINE = "\033[4m"
BLUE = "\033[94m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
GREY = "\033[90m"


def styled_output(s):
    print(f"""
{CYAN}{'='*100}
{BOLD}📦 IC DEBUG OUTPUT{RESET}
{YELLOW}{s}{RESET}
{CYAN}{'='*100}{RESET}\n
""")


ic.configureOutput(
    includeContext=True,
    prefix=f"{MAGENTA}→ {RESET}",
    outputFunction=styled_output,
    contextAbsPath=True
)
