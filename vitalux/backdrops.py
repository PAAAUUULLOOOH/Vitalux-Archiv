"""Low-overhead, locally rendered Vitalux background presets (no external images).

Every preset is a native Qt gradient. The scene and its blurred sampling image
share a single cache, keeping glass panels in sync with the backdrop.
"""
from math import sin, cos
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QLinearGradient, QPainter, QPainterPath, QPixmap, QRadialGradient

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
    if style == 'glass':
        colors = ('#071525', '#217ba2', '#635aa1', '#39a2b5')
    elif style == 'black_glass':
        colors = ('#06080d', '#38435a', '#5a5b77', '#65727d')
    elif style == 'dark':
        colors = ('#0b1321', '#16253c', '#1a2d45', '#10243c')
    elif style == 'light':
        colors = ('#f6f9fe', '#e9f2fe', '#d8e6fa', '#d9edf7')
    elif style == 'minimal':
        colors = ('#141719', '#232528', '#171a1d', '#202326')
    elif style == 'aurora':
        colors = ('#e9f6fd', '#7bcadf', '#a49be3', '#8cd8c8') if light else (
            '#081d2c', '#2398af', '#7862bb', '#33b9a6')
    elif style == 'obsidian':
        colors = ('#eff1f7', '#a9b7ce', '#9ca8c6', '#d4d9e6') if light else (
            '#090c15', '#404d65', '#55506c', '#697989')
    elif style == 'nebula':
        colors = ('#fbf2fc', '#ac8cde', '#e8a0ce', '#849de0') if light else (
            '#180f31', '#7442a8', '#af4f9f', '#4759b0')
    elif style == 'arctic':
        colors = ('#f5fbff', '#95d2ee', '#d9edfa', '#9abbde') if light else (
            '#102a3d', '#4b9cb5', '#85c1d7', '#4488b4')
    else:
        base = QColor(accent)
        if not base.isValid():
            base = QColor('#4f8cff')
        if light:
            colors = ('#f4f8ff', base.lighter(165).name(),
                      motion_colors('adaptive', accent, True)[1].lighter(148).name(),
                      base.lighter(125).name())
        else:
            colors = ('#0c1a2d', base.darker(118).name(),
                      motion_colors('adaptive', accent)[1].name(),
                      base.lighter(116).name())
    return tuple(QColor(c) for c in colors)


def motion_colors(style, accent, light=False):
    """The animated light follows the actual preset, not one generic hue."""
    if style in ('glass', 'aurora'):
        return QColor('#45b7e4'), QColor('#a77ae5')
    if style in ('black_glass', 'obsidian'):
        return QColor('#647994'), QColor('#a0a7bd')
    if style == 'nebula':
        return QColor('#a96be7'), QColor('#ee7db9')
    if style in ('arctic', 'light'):
        return QColor('#67bde6'), QColor('#a9d4ee')
    if style == 'dark':
        return QColor('#267da3'), QColor('#5e6bba')
    base = QColor(accent)
    if not base.isValid():
        base = QColor('#4f8cff')
    hue, sat, _val, _ = base.getHsv()
    if hue < 0:
        hue = 210
    return (QColor.fromHsv(hue, min(200, max(75, sat)), 225 if not light else 185),
            QColor.fromHsv((hue + 57) % 360, min(175, max(65, sat)),
                           218 if not light else 190))


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
