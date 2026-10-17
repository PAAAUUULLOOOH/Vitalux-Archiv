"""Low-overhead, locally rendered Vitalux background presets (no external images).

Every preset is a native Qt gradient. The scene and its blurred sampling image
share a single cache, keeping glass panels in sync with the backdrop.
"""
from math import sin, cos, pi
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QLinearGradient, QPainter, QPixmap, QRadialGradient

PRESETS = (
    ('legacy', 'Klassisch'),
    ('aurora', 'Aurora Glass'),
    ('obsidian', 'Obsidian Black'),
    ('nebula', 'Nebula Purple'),
    ('arctic', 'Arctic Frost'),
    ('adaptive', 'Adaptiv · Akzentfarbe'),
)
KEYS = tuple(key for key, _title in PRESETS)


def bounded(value, default=55):
    try:
        return max(0, min(100, int(value)))
    except (ValueError, TypeError, OverflowError):
        return default


def _colors(style, accent, light):
    if style == 'aurora':
        colors = ('#eaf7ff', '#67cfe6', '#8a93e8', '#97d7c1') if light else (
            '#091625', '#16689c', '#6244ae', '#22adad')
    elif style == 'obsidian':
        colors = ('#edf0f4', '#b0bbc9', '#828c9c', '#d1d8e3') if light else (
            '#07090d', '#364356', '#23262d', '#606b78')
    elif style == 'nebula':
        colors = ('#f7efff', '#ab7ad8', '#f4a3c4', '#7563c3') if light else (
            '#160d2a', '#5f329b', '#9b306f', '#383eab')
    elif style == 'arctic':
        colors = ('#f4faff', '#a4d8f0', '#d4e8fb', '#84b4d9') if light else (
            '#102233', '#316e9c', '#577aa8', '#55a8bd')
    else:
        base = QColor(accent)
        if not base.isValid():
            base = QColor('#4f8cff')
        if light:
            colors = ('#f2f7ff', base.lighter(155).name(), base.lighter(180).name(),
                      base.lighter(133).name())
        else:
            colors = ('#0b1526', base.darker(155).name(), base.darker(125).name(),
                      base.lighter(113).name())
    return tuple(QColor(c) for c in colors)


def render(size, style='adaptive', accent='#4f8cff', intensity=60,
           softness=65, light=False, phase=0.0):
    """Return sharp/soft QPixmaps for the same geometric gradient layout."""
    width, height = int(size.width()), int(size.height())
    if width < 1 or height < 1:
        return QPixmap(), QPixmap()
    style = style if style in KEYS and style != 'legacy' else 'adaptive'
    intensity = bounded(intensity, 60) / 100.
    softness = bounded(softness, 65) / 100.
    # Render at reduced resolution; smooth upscaling keeps painting inexpensive.
    scale = min(1., 900. / max(width, height))
    w, h = max(1, int(width * scale)), max(1, int(height * scale))
    base, first, second, third = _colors(style, accent, light)
    pixmap = QPixmap(w, h)
    pixmap.fill(base)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    underlay = QLinearGradient(0, h, w, 0)
    underlay.setColorAt(0, base)
    middle = QColor(first)
    middle.setAlphaF(.13 * intensity)
    underlay.setColorAt(1, middle)
    painter.fillRect(0, 0, w, h, QBrush(underlay))

    # Broad radial colors make an atmospheric wallpaper without hard shapes
    # underneath text, and react to the user's chosen accent color.
    radius = 1.05 + softness * .9
    lights = (
        (w * (.76 + .07 * sin(phase)), h * (.03 + .05 * cos(phase)),
         w * .72 * radius, first, .57),
        (w * (.14 + .06 * cos(phase * .8)), h * (.96 + .07 * sin(phase * .8)),
         w * .68 * radius, second, .42),
        (w * (.91 + .04 * sin(phase * .7)), h * (.73 + .04 * cos(phase * .7)),
         w * .47 * radius, third, .31),
    )
    for x, y, r, color, strength in lights:
        r = max(45., r)
        g = QRadialGradient(x, y, r)
        center = QColor(color)
        center.setAlphaF(min(.88, strength * intensity))
        end = QColor(color)
        end.setAlpha(0)
        g.setColorAt(0, center)
        g.setColorAt(.27, QColor(center))
        g.setColorAt(1, end)
        painter.fillRect(0, 0, w, h, QBrush(g))
    painter.end()
    sharp = pixmap.scaled(width, height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

    # Independently cached soft sampling for glass cards and sidebar. Stronger
    # blur resamples fewer pixels; no expensive live Gaussian filter required.
    divisor = 3 + round(softness * 13)
    small = sharp.scaled(max(12, width // divisor),
                         max(12, height // divisor),
                         Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    soft = small.scaled(width, height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    return sharp, soft
