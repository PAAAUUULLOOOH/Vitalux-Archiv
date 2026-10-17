"""Low-overhead, locally rendered Vitalux background presets (no external images).

Every preset is a native Qt gradient. The scene and its blurred sampling image
share a single cache, keeping glass panels in sync with the backdrop.
"""
from math import sin, cos, pi
from PySide6.QtCore import QPointF
from PySide6.QtGui import QPainterPath
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QLinearGradient, QPainter, QPixmap, QRadialGradient

DEFAULT_THEMES = ('dark', 'light', 'glass', 'black_glass', 'minimal')
PRESETS = (
    ('theme_default', 'Automatisch (Farbschema)'),
    ('dark', 'Dark'),
    ('light', 'Light'),
    ('glass', 'Glass'),
    ('black_glass', 'Black Glass'),
    ('minimal', 'Minimalistisch'),
    ('aurora', 'Aurora Glass'),
    ('obsidian', 'Obsidian Black'),
    ('nebula', 'Nebula Purple'),
    ('arctic', 'Arctic Frost'),
    ('adaptive', 'Adaptiv · Akzentfarbe'),
)
KEYS = tuple(key for key, _title in PRESETS)


def resolve(style, theme_mode):
    """Keep older Classic installations intact and match the active theme."""
    if style in ('legacy', 'theme_default') or style not in KEYS:
        return theme_mode
    return style


def bounded(value, default=55):
    try:
        return max(0, min(100, int(value)))
    except (ValueError, TypeError, OverflowError):
        return default


def _colors(style, accent, light):
    if style == 'dark':
        colors = ('#0b1321', '#16253c', '#1a2d45', '#10243c')
    elif style == 'light':
        colors = ('#f6f9fe', '#e9f2fe', '#d8e6fa', '#d9edf7')
    elif style == 'minimal':
        colors = ('#141719', '#232528', '#171a1d', '#202326')
    elif style == 'aurora':
        colors = ('#eaf7ff', '#67cfe6', '#8a93e8', '#97d7c1') if light else (
            '#091625', '#16689c', '#6244ae', '#22adad')
    elif style == 'obsidian':
        colors = ('#e9edf4', '#b2c1d6', '#91a3bf', '#d1d8e3') if light else (
            '#07090d', '#2c3747', '#191d25', '#637184')
    elif style == 'nebula':
        colors = ('#f8f2ff', '#9b82cb', '#e9a4ce', '#7588d1') if light else (
            '#130e27', '#693ba2', '#ad4b85', '#414dac')
    elif style == 'arctic':
        colors = ('#f5faff', '#9bcfe7', '#ddeefa', '#9bbfdc') if light else (
            '#102233', '#377cab', '#8bb5d2', '#31758d')
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
    style = style if style in KEYS else 'adaptive'
    intensity = bounded(intensity, 60) / 100.
    softness = bounded(softness, 65) / 100.
    # Render at reduced resolution; smooth upscaling keeps painting inexpensive.
    scale = min(1., 900. / max(width, height))
    w, h = max(1, int(width * scale)), max(1, int(height * scale))
    base, first, second, third = _colors(style, accent, light)
    if style in ('dark', 'light', 'minimal'):
        # The original flat Dark/Light/Minimal backgrounds remain familiar.
        canvas = QPixmap(width, height)
        canvas.fill(base)
        if style != 'minimal':
            p = QPainter(canvas)
            wash = QLinearGradient(0, 0, width, height)
            end = QColor('#090d16' if style == 'dark' else '#eaf1f9')
            wash.setColorAt(0, base)
            wash.setColorAt(1, end)
            p.fillRect(0, 0, width, height, QBrush(wash))
            p.end()
        return canvas, canvas
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

    # Two wide, translucent satin ribbons lend depth without busy textures.
    # Their edges remain far softer than dashboard charts or labels.
    for index, color in enumerate((second, third)):
        ribbon = QPainterPath()
        ypos = h * (.27 if index == 0 else .74)
        bend = h * (.12 if index == 0 else -.12)
        ribbon.moveTo(-w * .12, ypos)
        ribbon.cubicTo(w * .28, ypos + bend * 1.5,
                       w * .58, ypos - bend * 1.7,
                       w * 1.12, ypos + bend * .25)
        ribbon.cubicTo(w * .65, ypos - bend * .80 + h*.17,
                       w * .27, ypos + bend + h*.14,
                       -w * .12, ypos + h*.12)
        ribbon.closeSubpath()
        gloss = QLinearGradient(0, ypos-h*.1, w, ypos+h*.2)
        bright = QColor(color)
        bright.setAlphaF(.09 * intensity)
        clear = QColor(color)
        clear.setAlpha(0)
        gloss.setColorAt(0, clear)
        gloss.setColorAt(.48, bright)
        gloss.setColorAt(1, clear)
        painter.fillPath(ribbon, QBrush(gloss))
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
