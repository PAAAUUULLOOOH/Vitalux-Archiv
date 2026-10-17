"""Lädt das Distro-Logo aus dem System. Gibt es keins, wird ein Badge in Distro-Farbe gezeichnet."""
import os

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QIcon, QLinearGradient, QPainter, QPixmap

SEARCH_DIRS = [
    "/usr/share/pixmaps", "/usr/share/pixmaps/distribution-logos",
    "/usr/share/icons/hicolor/scalable/apps", "/usr/share/icons/hicolor/512x512/apps",
    "/usr/share/icons/hicolor/256x256/apps", "/usr/share/icons/hicolor/128x128/apps",
    "/usr/share/icons/hicolor/96x96/apps", "/usr/share/icons/hicolor/64x64/apps",
    "/usr/share/icons/hicolor/48x48/apps",
]


def _names(info):
    i = info["id"]
    names = [info.get("logo")] if info.get("logo") else []
    names += [f"distributor-logo-{i}", f"{i}-logo-icon", f"{i}-logo", f"start-here-{i}", i,
              f"distributor-logo-{i.capitalize()}"]
    return names


def _from_theme(name, px):
    icon = QIcon.fromTheme(name)
    if icon.isNull():
        return None
    pm = icon.pixmap(QSize(px, px))
    return None if pm.isNull() else pm


def _from_files(name, px):
    for d in SEARCH_DIRS:
        for ext in (".svg", ".png", ".xpm"):
            path = os.path.join(d, name + ext)
            if os.path.isfile(path):
                pm = QIcon(path).pixmap(QSize(px, px))
                if not pm.isNull():
                    return pm
    return None


def _badge(info, px):
    pm = QPixmap(px, px)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    base = QColor(info["color"])
    grad = QLinearGradient(0, 0, px, px)
    grad.setColorAt(0, base.lighter(125))
    grad.setColorAt(1, base.darker(135))
    p.setBrush(QBrush(grad))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(0, 0, px, px), px * 0.28, px * 0.28)
    font = QFont()
    font.setPixelSize(int(px * 0.55))
    font.setBold(True)
    p.setFont(font)
    p.setPen(QColor("white"))
    letter = ((info.get("short") or info["id"] or "L")[:1]).upper()
    p.drawText(QRectF(0, 0, px, px), Qt.AlignCenter, letter)
    p.end()
    return pm


def load_logo(info, size=96):
    """Liefert ein scharfes QPixmap (2x supersampled) mit dem Distro-Logo."""
    px = size * 2
    pm = None
    for name in _names(info):
        pm = _from_theme(name, px)
        if pm is None:
            pm = _from_files(name, px)
        if pm is not None:
            pm = pm.scaled(px, px, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            break
    if pm is None:
        pm = _badge(info, px)
    pm.setDevicePixelRatio(2)
    return pm
