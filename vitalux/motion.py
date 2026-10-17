"""User-selectable, low-overhead motion profiles.

All durations are resolved at animation start, so changes take effect without
rebuilding pages or restarting live measurements.
"""
from . import settings

MODES = ("smooth", "reduced", "off")


def level():
    value = settings.get("motion", "smooth")
    return value if value in MODES else "smooth"


def duration(milliseconds):
    base = max(0, int(milliseconds))
    profile = level()
    if profile == "off" or settings.get("theme", "glass") == "minimal":
        return 0
    if profile == "reduced":
        return max(50, min(110, round(base * .43)))
    return base


def enabled():
    return level() != "off" and settings.get("theme", "glass") != "minimal"
