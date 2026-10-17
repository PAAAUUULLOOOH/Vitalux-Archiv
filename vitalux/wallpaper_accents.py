"""Stable accent suggestions sampled from the displayed local wallpaper.

Color analysis runs only when a wallpaper/theme selection changes. It never
polls hardware or tracks display pixels. A fixed neutral render prevents a
feedback loop with the 'Adaptive · accent color' background.
"""
from functools import lru_cache

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor
from . import backdrops, settings, theme, user_background

AUTO = 'wallpaper_auto'
COUNT = 5


def is_legacy_accent(value):
    """Old numbered swatches are replaced with one automatic accent choice."""
    return value in {f'wallpaper_{n}' for n in range(COUNT)}


def is_wallpaper_accent(value):
    return value == AUTO or is_legacy_accent(value)


def suggestions():
    selected_style = settings.get('background_style', 'theme_default')
    style = backdrops.resolve(selected_style, theme.mode())
    selected = settings.get('custom_background_selected', '') if style == 'custom_image' else ''
    fit = settings.get('custom_background_fit', 'cover') if style == 'custom_image' else ''
    path = user_background.image_path(selected) if selected else None
    stamp = (path.stat().st_mtime_ns, path.stat().st_size) if path else None
    return list(_sample(style, selected, fit, stamp, theme.mode()))


@lru_cache(maxsize=32)
def _sample(style, filename, fit, stamp, theme_mode):
    size = QSize(144, 90)
    if style == 'custom_image':
        if stamp is None:
            return ('#4f8cff',) * COUNT
        picture = user_background.draw(size, filename, fit)
    else:
        # Keep the analysis stable even when the current accent changes.
        picture, _ = backdrops.render(
            size, style, '#4f8cff',
            light=style in backdrops.LIGHT_PRESETS or theme_mode == 'light',
            phase=0.0)
    if picture.isNull():
        return ('#4f8cff',) * COUNT

    image = picture.toImage()
    buckets = {}
    for y in range(0, image.height(), 2):
        for x in range(0, image.width(), 2):
            c = image.pixelColor(x, y)
            if c.alpha() < 160:
                continue
            h, s, v, _ = c.getHsv()
            if s < 36 or v < 28:
                continue
            # Group similar hues. Avoid isolated bright pixels dominating.
            key = (max(0, h) // 22, s // 75, v // 65)
            sums = buckets.setdefault(key, [0, 0, 0, 0, 0])
            sums[0] += c.red()
            sums[1] += c.green()
            sums[2] += c.blue()
            sums[3] += 1
            sums[4] += s

    ranked = sorted(
        buckets.values(),
        key=lambda a: a[3] * (0.5 + a[4] / max(1, a[3]) / 255),
        reverse=True)
    chosen = []
    for r, g, b, count, _ in ranked:
        if count < 2:
            continue
        color = QColor(round(r/count), round(g/count), round(b/count))
        h, s, v, _ = color.getHsv()
        if h < 0:
            continue
        candidate = QColor.fromHsv(h, max(125, min(228, s)),
                                   max(150, min(232, v)))
        if all(min(abs(h - c.hue()), 360-abs(h - c.hue())) >= 23
               for c in chosen):
            chosen.append(candidate)
            if len(chosen) >= COUNT:
                break

    if not chosen:
        center = image.pixelColor(image.width()//2, image.height()//2)
        brightness = center.value()
        chosen = [QColor('#9ba8b9') if brightness < 140 else QColor('#67788e')]

    # Photographs with only one hue still offer tasteful tonal variations.
    bases = list(chosen)
    index = 0
    while len(chosen) < COUNT:
        base = bases[index % len(bases)]
        h, s, v, _ = base.getHsv()
        phase = index // len(bases) + 1
        cand = QColor.fromHsv(max(0, h), min(235, max(90, s + (20 if phase % 2 else -20))),
                              max(135, min(244, v + (20 if phase % 2 else -20)*phase)))
        if cand.name() not in {c.name() for c in chosen}:
            chosen.append(cand)
        index += 1
        if index > 50:
            chosen.append(QColor('#4f8cff'))
    return tuple(c.name() for c in chosen[:COUNT])


def resolve_accent(stored, distro_color='#4f8cff'):
    if stored == 'auto':
        return distro_color
    if is_wallpaper_accent(stored):
        colors = suggestions()
        return colors[0]
    color = QColor(str(stored))
    return color.name() if color.isValid() else '#4f8cff'
