"""Locally stored, safe user background images with configurable placement."""
from pathlib import Path
from functools import lru_cache
from uuid import uuid4
import shutil
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QImageReader, QPainter, QPixmap
from . import settings, theme

FORMATS = {'.png', '.jpg', '.jpeg', '.webp', '.bmp'}
FITS = [('Bildschirmfüllend', 'cover'), ('Einpassen', 'contain'),
        ('Strecken', 'stretch'), ('Zentriert', 'center'), ('Kacheln', 'tile')]


def folder():
    return Path(settings.PATH).parent / 'backgrounds'


def image_path(filename):
    if not isinstance(filename, str) or Path(filename).name != filename:
        return None
    if Path(filename).suffix.lower() not in FORMATS:
        return None
    p = folder() / filename
    return p if p.is_file() else None


def images():
    saved = settings.get('custom_backgrounds', [])
    result = []
    seen = set()
    for item in saved if isinstance(saved, list) else []:
        if not isinstance(item, dict):
            continue
        filename = item.get('file')
        if filename not in seen and image_path(filename):
            result.append({'file': filename, 'name': str(item.get('name') or filename)[:80]})
            seen.add(filename)
    return result


def import_image(filename):
    source = Path(filename)
    if source.suffix.lower() not in FORMATS or not source.is_file():
        raise ValueError('Ungültiges Bildformat.')
    if source.stat().st_size > 40 * 1024 * 1024:
        raise ValueError('Die Datei darf höchstens 40 MB groß sein.')
    reader = QImageReader(str(source))
    dimensions = reader.size()
    if not reader.canRead() or not dimensions.isValid() or dimensions.width() * dimensions.height() > 60_000_000:
        raise ValueError('Bild kann nicht gelesen werden oder ist zu groß.')
    folder().mkdir(parents=True, exist_ok=True)
    dest = uuid4().hex + source.suffix.lower()
    shutil.copyfile(source, folder() / dest)
    return {'name': source.stem[:80], 'file': dest}


@lru_cache(maxsize=6)
def _scaled_image(path, modified, source_bytes, width, height, mode):
    """Cache bounded decoded wallpapers; JPEG readers can subsample at decode.

    Images which are already smaller than the target retain their natural size.
    'center' and 'tile' intentionally keep the original pixel dimensions.
    """
    reader = QImageReader(path)
    reader.setAutoTransform(True)
    native = reader.size()
    if native.isValid() and mode in ('cover', 'contain', 'stretch'):
        if mode == 'stretch':
            target = QSize(width, height)
        else:
            factor = (max if mode == 'cover' else min)(
                width / native.width(), height / native.height())
            target = QSize(max(1, round(native.width() * factor)),
                           max(1, round(native.height() * factor)))
        # Never enlarge at decode time and avoid accidentally decoding to zero.
        if (target.width() > 0 and target.height() > 0
                and (target.width() < native.width() or
                     target.height() < native.height())):
            reader.setScaledSize(target)
    image = reader.read()
    return QPixmap.fromImage(image) if not image.isNull() else QPixmap()


def draw(size, filename, mode='cover'):
    """Render a wallpaper at its display size, with local image decode caching."""
    size = QSize(size)
    canvas = QPixmap(size)
    if canvas.isNull():
        return canvas
    canvas.fill(QColor(theme.BG))
    path = image_path(filename)
    if path is None:
        return canvas
    metadata = path.stat()
    source = _scaled_image(str(path), metadata.st_mtime_ns, metadata.st_size,
                           size.width(), size.height(), mode)
    if source.isNull():
        return canvas
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    if mode == 'tile':
        painter.drawTiledPixmap(canvas.rect(), source)
    else:
        ratio = (Qt.IgnoreAspectRatio if mode == 'stretch' else
                 Qt.KeepAspectRatio if mode == 'contain' else Qt.KeepAspectRatioByExpanding)
        scaled = source if mode == 'center' else source.scaled(size, ratio, Qt.SmoothTransformation)
        painter.drawPixmap((canvas.width()-scaled.width())//2,
                           (canvas.height()-scaled.height())//2, scaled)
    painter.end()
    return canvas
