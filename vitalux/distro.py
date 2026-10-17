"""Distro-Erkennung über /etc/os-release (ohne Qt)."""
import re

DEFAULT = "#4f8cff"

# Akzentfarben (ungefähre Markenfarben), nur für das Farbschema der App.
BRAND = {
    "ubuntu": "#e95420", "debian": "#d70a53", "fedora": "#3c6eb4", "nobara": "#7a9ee0",
    "arch": "#1793d1", "cachyos": "#16b8a0", "endeavouros": "#8a7cf0", "manjaro": "#35bf5c",
    "garuda": "#a78bfa", "opensuse": "#73ba25", "sles": "#30ba78", "linuxmint": "#86be43",
    "pop": "#48b9c7", "zorin": "#15a6f0", "elementary": "#64baff", "kali": "#367bf0",
    "nixos": "#7ebae4", "gentoo": "#7a6bc0", "alpine": "#1a7fb0", "void": "#5fa37f",
    "rocky": "#10b981", "almalinux": "#2f7fc1", "rhel": "#ee0000", "centos": "#b0479a",
    "mageia": "#2397d4", "slackware": "#7a7ad0", "solus": "#5294e2", "mx": "#8f8f9f",
}

ANSI_BASIC = {30: "#6b7280", 31: "#ef4444", 32: "#22c55e", 33: "#eab308",
              34: "#3b82f6", 35: "#a855f7", 36: "#06b6d4", 37: "#e5e7eb"}


def _parse(path):
    data = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                data[k] = v.strip().strip('"').strip("'")
    except OSError:
        return None
    return data


def _color(id_, like, ansi):
    for key in [id_] + like:
        for brand, col in BRAND.items():
            if key == brand or key.startswith(brand):
                return col
    if ansi:
        m = re.search(r"38;2;(\d+);(\d+);(\d+)", ansi)
        if m:
            r, g, b = (min(255, int(x)) for x in m.groups())
            return f"#{r:02x}{g:02x}{b:02x}"
        nums = [int(n) for n in re.findall(r"\d+", ansi)]
        for n in reversed(nums):
            if n in ANSI_BASIC:
                return ANSI_BASIC[n]
    return DEFAULT


def info():
    raw = _parse("/etc/os-release") or _parse("/usr/lib/os-release") or {}
    id_ = raw.get("ID", "linux").lower()
    like = raw.get("ID_LIKE", "").lower().split()
    name = raw.get("PRETTY_NAME") or raw.get("NAME") or "Linux"
    return {
        "id": id_,
        "like": like,
        "name": name,
        "short": raw.get("NAME", name),
        "version": raw.get("VERSION") or raw.get("VERSION_ID", ""),
        "logo": raw.get("LOGO"),
        "color": _color(id_, like, raw.get("ANSI_COLOR")),
    }
