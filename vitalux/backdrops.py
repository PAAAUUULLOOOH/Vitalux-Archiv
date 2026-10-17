"""Low-overhead, locally rendered Vitalux background presets (no external images).

Every preset is a native Qt gradient. The scene and its blurred sampling image
share a single cache, keeping glass panels in sync with the backdrop.
"""
from math import sin, cos
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QLinearGradient, QPainter, QPainterPath, QPixmap, QRadialGradient

DEFAULT_THEMES = ('dark', 'light', 'glass', 'black_glass', 'minimal')
# The five original wallpaper/theme pairs are preserved unchanged.
# Additional designs replace the discontinued Aurora/Obsidian/Nebula/Arctic/Adaptive set.
PRESETS = (
    ('theme_default', 'Automatisch (Farbschema)'),
    ('dark', 'Dark'),
    ('light', 'Light'),
    ('glass', 'Glass'),
    ('black_glass', 'Black Glass'),
    ('minimal', 'Minimalistisch'),
    ('pearl', 'Hell · Perlmutt'),
    ('daybreak', 'Hell · Morgenlicht'),
    ('ice', 'Hell · Eisblau'),
    ('pastel_rainbow', 'Regenbogen · Pastell'),
    ('prism', 'Regenbogen · Prisma'),
    ('deep_ocean', 'Dunkel · Tiefsee'),
    ('midnight', 'Dunkel · Mitternacht'),
    ('velvet', 'Dunkel · Samt'),
    ('graphite', 'Dunkel · Graphit'),
)
KEYS = tuple(key for key, _title in PRESETS)
LIGHT_PRESETS = frozenset(('light', 'pearl', 'daybreak', 'ice', 'pastel_rainbow'))
RAINBOW_PRESETS = frozenset(('pastel_rainbow', 'prism'))


def resolve(style, theme_mode):
    """Discontinued wallpaper selections fall back to the original theme."""
    return theme_mode if style not in KEYS or style == 'theme_default' else style


def bounded(value, default=55):
    try:
        return max(0, min(100, int(value)))
    except (ValueError, TypeError, OverflowError):
        return default


# Colors within each collection share similar saturation and luminance.
# The middle of the window stays quiet so hardware telemetry stays readable.
_PALETTES = {
    'dark': ('#0b1321', '#16253c', '#1a2d45', '#10243c'),
    'light': ('#f6f9fe', '#e9f2fe', '#d8e6fa', '#d9edf7'),
    'glass': ('#071525', '#217ba2', '#635aa1', '#39a2b5'),
    'black_glass': ('#06080d', '#38435a', '#5a5b77', '#65727d'),
    'minimal': ('#141719', '#232528', '#171a1d', '#202326'),
    'pearl': ('#f6f4f4', '#efe0e8', '#dbe9f1', '#eee2d7'),
    'daybreak': ('#fff7ef', '#ffcfb8', '#f1b6d2', '#b5d5ef'),
    'ice': ('#f2faff', '#b3e3ee', '#c5d7f6', '#b8e4e0'),
    'pastel_rainbow': ('#f9f4fd', '#f4bed3', '#b8d3fc', '#b9ebd9'),
    'prism': ('#171a34', '#ef659b', '#638ef4', '#4fd3bd'),
    'deep_ocean': ('#071b2a', '#166886', '#21437e', '#1f8883'),
    'midnight': ('#0b1123', '#34417f', '#4d3686', '#273b60'),
    'velvet': ('#200f23', '#75345c', '#493778', '#a24f65'),
    'graphite': ('#101318', '#343d4c', '#526176', '#414b60'),
}


def _colors(style, accent, light):
    palette = [QColor(value) for value in _PALETTES.get(style, _PALETTES['glass'])]
    if style in DEFAULT_THEMES:
        return tuple(palette)
    # A very slight echo of the selected accent ties the backgrounds to UI
    # controls without turning every pastel or rainbow wallpaper the same hue.
    selected = QColor(accent)
    if selected.isValid():
        amount = .075 if style in LIGHT_PRESETS else .10
        for index in (1, 3):
            color = palette[index]
            palette[index] = QColor(
                round(color.red() * (1 - amount) + selected.red() * amount),
                round(color.green() * (1 - amount) + selected.green() * amount),
                round(color.blue() * (1 - amount) + selected.blue() * amount),
            )
    return tuple(palette)


def material_tint(style, base, accent, amount=.16):
    """Glass material accent, kept close to the selected UI theme for contrast."""
    original = QColor(base)
    if style in DEFAULT_THEMES or style not in KEYS:
        return original
    source = _colors(style, accent, False)[1]
    return QColor(
        round(original.red() * (1 - amount) + source.red() * amount),
        round(original.green() * (1 - amount) + source.green() * amount),
        round(original.blue() * (1 - amount) + source.blue() * amount),
    )


def motion_colors(style, accent, light=False):
    colors = _colors(style, accent, light)
    return colors[1], colors[2]


def minimal_color(intensity):
    """Keep Minimal flat/monochrome, but let its intensity adjust luminance."""
    fraction = bounded(intensity, 60) / 100
    level = round(12 + 19 * fraction)
    return QColor(level, level + 2, level + 3)


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
        # Original flat designs remain understated. Even these defaults must
        # respond to the intensity slider, not silently ignore its setting.
        if style == 'minimal':
            flat = QPixmap(width, height)
            flat.fill(minimal_color(intensity * 100))
            return flat, flat
        canvas = QPixmap(width, height)
        canvas.fill(base)
        p = QPainter(canvas)
        wash = QLinearGradient(0, 0, width, height)
        end = QColor('#090d16' if style == 'dark' else '#eaf1f9')
        wash.setColorAt(0, base)
        wash.setColorAt(1, end)
        p.fillRect(0, 0, width, height, QBrush(wash))
        # A deliberately muted paired color wash, visibly controlled by 0–100%.
        for x, y, color, weight in (
                (.16, .13, first, .46),
                (.84, .81, second, .35)):
            glow = QRadialGradient(width*x, height*y,
                                   max(width*.70, height*.90) * (1 + softness*.25))
            inner = QColor(color)
            inner.setAlphaF(min(.52, intensity * weight))
            middle = QColor(inner); middle.setAlphaF(inner.alphaF() * .48)
            outer = QColor(inner); outer.setAlpha(0)
            glow.setColorAt(0, inner)
            glow.setColorAt(.55, middle)
            glow.setColorAt(1, outer)
            p.fillRect(0, 0, width, height, QBrush(glow))
        p.end()
        return canvas, canvas
    pixmap = QPixmap(w, h)
    pixmap.fill(base)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    underlay = QLinearGradient(0, h, w, 0)
    mid = QColor(first); mid.setAlphaF(.24 * intensity)
    other = QColor(second); other.setAlphaF(.22 * intensity)
    underlay.setColorAt(0, other)
    underlay.setColorAt(.5, base)
    underlay.setColorAt(1, mid)
    painter.fillRect(0, 0, w, h, QBrush(underlay))

    # Broad radial colors make an atmospheric wallpaper without hard shapes
    # underneath text, and react to the user's chosen accent color.
    radius = 1.04 + softness * .72
    lights = (
        (w * (.12 + .16 * sin(phase)), h * (.20 + .09 * cos(phase)),
         w * .64 * radius, first, .62),
        (w * (.87 + .14 * sin(phase + 1.95)), h * (.20 + .13 * cos(phase + .65)),
         w * .64 * radius, second, .59),
        (w * (.54 + .12 * sin(phase * .67 + 1.7)), h * (.83 + .08 * cos(phase * .81)),
         w * .74 * radius, third, .52),
        (w * (.12 + .05 * sin(phase * .7)), h * (.78 + .11 * cos(phase * .67)),
         w * .54 * radius, second, .28),
    )
    for x, y, r, color, strength in lights:
        r = max(45., r)
        g = QRadialGradient(x, y, r)
        center = QColor(color)
        center.setAlphaF(min(.88, strength * intensity))
        end = QColor(color)
        end.setAlpha(0)
        g.setColorAt(0, center)
        g.setColorAt(.26, QColor(center))
        mid = QColor(center); mid.setAlphaF(center.alphaF() * .65)
        g.setColorAt(.56, mid)
        g.setColorAt(1, end)
        painter.fillRect(0, 0, w, h, QBrush(g))

    # A restrained, almost invisible satin layer retains legibility.
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
        bright.setAlphaF(.055 * intensity)
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
