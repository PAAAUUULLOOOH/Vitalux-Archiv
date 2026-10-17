"""Low-overhead, locally rendered Vitalux background presets (no external images).

Every preset is a native Qt gradient. The scene and its blurred sampling image
share a single cache, keeping glass panels in sync with the backdrop.
"""
from math import sin, cos
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QBrush, QLinearGradient, QPainter, QPainterPath, QPixmap, QRadialGradient

DEFAULT_THEMES = ('dark', 'light', 'glass', 'black_glass', 'minimal')
# The five original wallpaper/theme pairs are preserved unchanged.
# The original themes and supported static designs remain available.
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
    ('prism', 'Regenbogen · Prisma'),
    ('deep_ocean', 'Dunkel · Tiefsee'),
    ('midnight', 'Dunkel · Mitternacht'),
    ('velvet', 'Dunkel · Samt'),
    ('graphite', 'Dunkel · Graphit'),
    ('animated_sparkle', 'Animiert · Funkeln'),
    ('animated_aurora', 'Animiert · Nordlicht'),
    ('animated_waves', 'Animiert · Nachtwellen'),
    ('animated_mist', 'Animiert · Violetter Nebel'),
    ('adaptive', 'Adaptiv · Akzentfarbe'),
)
KEYS = tuple(key for key, _title in PRESETS)
ANIMATED_PRESETS = frozenset((
    'animated_sparkle', 'animated_aurora', 'animated_waves', 'animated_mist',
))
LIGHT_PRESETS = frozenset(('light', 'pearl', 'daybreak', 'ice'))
RAINBOW_PRESETS = frozenset(('prism',))


def resolve(style, theme_mode):
    """Discontinued wallpaper selections fall back to the original theme."""
    return theme_mode if style not in KEYS or style == 'theme_default' else style


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
    'prism': ('#171a34', '#ef659b', '#638ef4', '#4fd3bd'),
    'deep_ocean': ('#071b2a', '#166886', '#21437e', '#1f8883'),
    'midnight': ('#0b1123', '#34417f', '#4d3686', '#273b60'),
    'velvet': ('#200f23', '#75345c', '#493778', '#a24f65'),
    'graphite': ('#101318', '#343d4c', '#526176', '#414b60'),
    'animated_sparkle': ('#11162f', '#5855bd', '#934fa8', '#298aa6'),
    # Low-key palettes sampled against the original Glass brightness.
    'animated_aurora': ('#091a2a', '#1f5668', '#385575', '#1c6672'),
    'animated_waves': ('#09182a', '#1b4163', '#275272', '#16475b'),
    'animated_mist': ('#151326', '#47365f', '#334b6c', '#574362'),
}


def _colors(style, accent, light):
    if style == 'adaptive':
        base = QColor(accent)
        if not base.isValid():
            base = QColor('#4f8cff')
        hue, saturation, _value, _alpha = base.getHsv()
        hue = hue if hue >= 0 else 214
        first = QColor.fromHsv(hue, min(200, max(92, saturation)), 240)
        second = QColor.fromHsv((hue + 41) % 360, 150, 242)
        third = QColor.fromHsv((hue + 333) % 360, 145, 231)
        if light:
            return (QColor('#f4f8fe'),
                    QColor.fromHsv(hue, 92, 245),
                    QColor.fromHsv((hue + 41) % 360, 91, 248),
                    QColor.fromHsv((hue + 333) % 360, 100, 241))
        return (QColor('#102039'), first, second, third)
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


def minimal_color():
    """Stable monochrome default for the Minimal wallpaper."""
    return QColor(24, 26, 27)


def paint_animated_layer(p, width, height, style, phase):
    """Four purpose-built animated wallpapers in restrained Glass-level hues."""
    if style == 'animated_sparkle':
        # Retain the established sparkle design exactly as before.
        p.setPen(Qt.NoPen)
        for i in range(82):
            x = (i * 0.61803398875 % 1) * width
            y = (i * 0.75487766625 % 1) * height
            wave = .5 + .5 * sin(phase * 2.7 + i * 1.77)
            alpha = round(17 + 221 * wave ** 3)
            radius = (.7 + 1.5 * wave) * max(.75, min(1.5, width / 820))
            c = QColor('#def6ff' if i % 3 else '#edbaff')
            halo = QColor(c); halo.setAlpha(round(alpha * .22))
            c.setAlpha(alpha)
            p.setBrush(halo)
            p.drawEllipse(QPointF(x, y), radius * 3.1, radius * 3.1)
            p.setBrush(c)
            p.drawEllipse(QPointF(x, y), radius, radius)

    elif style == 'animated_aurora':
        # Broad, translucent northern lights: dark teal / subdued blue-purple.
        for i, code in enumerate(('#399b94', '#4778a6', '#7664a0')):
            x = width * (.18 + .32*i + .17*sin(phase*.66+i*1.7))
            y = height * (.32 + .13*cos(phase*.51+i*.9))
            radius = max(width*.48, height*1.05)
            glow = QRadialGradient(x, y, radius)
            center = QColor(code); center.setAlpha(80 if i == 0 else 57)
            edge = QColor(center); edge.setAlpha(0)
            glow.setColorAt(0, center)
            glow.setColorAt(.38, QColor(center))
            glow.setColorAt(1, edge)
            p.fillRect(0, 0, width, height, QBrush(glow))
        for i, code in enumerate(('#3eaa9a', '#607cbb')):
            x = width * (.19 + i*.41 + .15*sin(phase*.72+i*2.1))
            curve = QPainterPath()
            curve.moveTo(x-width*.23, -height*.12)
            curve.cubicTo(x+width*.13, height*.28,
                          x-width*.19, height*.59,
                          x+width*.10, height*1.12)
            curve.lineTo(x+width*.39, height*1.12)
            curve.cubicTo(x+width*.11, height*.61,
                          x+width*.39, height*.28,
                          x+width*.03, -height*.12)
            curve.closeSubpath()
            wash = QLinearGradient(x-width*.26, 0, x+width*.40, 0)
            hue = QColor(code)
            hue.setAlpha(0); wash.setColorAt(0, hue)
            hue.setAlpha(40); wash.setColorAt(.48, hue)
            hue.setAlpha(0); wash.setColorAt(1, hue)
            p.fillPath(curve, QBrush(wash))

    elif style == 'animated_waves':
        # Long slow ocean waves, cool but not electric-blue.
        for i, color in enumerate(('#23678a', '#326a83', '#36628d')):
            baseline = height * (.37 + i*.19)
            offset = height * .075 * sin(phase*.68 + i*1.9)
            ridge = QPainterPath()
            ridge.moveTo(-width*.12, baseline+offset)
            ridge.cubicTo(width*.22, baseline-height*.11+offset,
                          width*.47, baseline+height*.12-offset,
                          width*.72, baseline-height*.06+offset)
            ridge.cubicTo(width*.90, baseline-height*.12-offset,
                          width*1.05, baseline+offset,
                          width*1.12, baseline-height*.08+offset)
            ridge.lineTo(width*1.12, height*1.2)
            ridge.lineTo(-width*.12, height*1.2)
            ridge.closeSubpath()
            wave = QLinearGradient(0, baseline-height*.2, 0, height*1.1)
            c = QColor(color); c.setAlpha(0)
            wave.setColorAt(0, c)
            c.setAlpha(54 if i == 0 else 39)
            wave.setColorAt(.38, c)
            c.setAlpha(5)
            wave.setColorAt(1, c)
            p.fillPath(ridge, QBrush(wave))

    elif style == 'animated_mist':
        # A cluster of diffused lavender/indigo clouds, no bright hot-spots.
        for i, color in enumerate(('#735f92', '#4c7794', '#895f8d', '#456784')):
            x = width * (.19 + (i % 3)*.3 + .16*sin(phase*.57+i*1.2))
            y = height * (.26 + (i % 2)*.4 + .15*cos(phase*.49+i*1.7))
            spread = max(width*.48, height*.92)
            cloud = QRadialGradient(x, y, spread)
            center = QColor(color)
            center.setAlpha(90 if i < 2 else 64)
            middle = QColor(center); middle.setAlpha(round(center.alpha()*.42))
            edge = QColor(center); edge.setAlpha(0)
            cloud.setColorAt(0, center)
            cloud.setColorAt(.49, middle)
            cloud.setColorAt(1, edge)
            p.fillRect(0, 0, width, height, QBrush(cloud))

def render(size, style='glass', accent='#4f8cff', light=False, phase=0.0):
    """Return sharp/soft QPixmaps for the same geometric gradient layout."""
    width, height = int(size.width()), int(size.height())
    if width < 1 or height < 1:
        return QPixmap(), QPixmap()
    style = style if style in KEYS else 'glass'
    # Render at reduced resolution; smooth upscaling keeps painting inexpensive.
    scale = min(1., 900. / max(width, height))
    w, h = max(1, int(width * scale)), max(1, int(height * scale))
    base, first, second, third = _colors(style, accent, light)
    if style in ('dark', 'light', 'minimal'):
        # Original flat designs remain understated and stable.
        if style == 'minimal':
            flat = QPixmap(width, height)
            flat.fill(minimal_color())
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
                                   max(width*.70, height*.90) * 1.16)
            inner = QColor(color)
            inner.setAlphaF(min(.52, .68 * weight))
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
    mid = QColor(first); mid.setAlphaF(.16)
    other = QColor(second); other.setAlphaF(.15)
    underlay.setColorAt(0, other)
    underlay.setColorAt(.5, base)
    underlay.setColorAt(1, mid)
    painter.fillRect(0, 0, w, h, QBrush(underlay))

    # Broad radial colors, tuned per wallpaper without user intensity settings.
    radius = 1.50
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
        center.setAlphaF(min(.88, strength * .82))
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
        bright.setAlphaF(.042)
        clear = QColor(color)
        clear.setAlpha(0)
        gloss.setColorAt(0, clear)
        gloss.setColorAt(.48, bright)
        gloss.setColorAt(1, clear)
        painter.fillPath(ribbon, QBrush(gloss))
    if style in ANIMATED_PRESETS:
        paint_animated_layer(painter, w, h, style, phase)
    painter.end()
    sharp = pixmap.scaled(width, height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)

    # Fixed soft sampling for glass panels; no user-adjustable blur.
    divisor = 11
    small = sharp.scaled(max(12, width // divisor),
                         max(12, height // divisor),
                         Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    soft = small.scaled(width, height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    return sharp, soft
