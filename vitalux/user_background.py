"""Locally stored, safe user background images with configurable placement."""
from pathlib import Path
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


def draw(size, filename, mode='cover'):
    canvas = QPixmap(QSize(size))
    if canvas.isNull():
        return canvas
    canvas.fill(QColor(theme.BG))
    path = image_path(filename)
    if path is None:
        return canvas
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)
    picture = reader.read()
    if picture.isNull():
        return canvas
    source = QPixmap.fromImage(picture)
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    if mode == 'tile':
        painter.drawTiledPixmap(canvas.rect(), source)
    else:
        ratio = (Qt.IgnoreAspectRatio if mode == 'stretch' else
                 Qt.KeepAspectRatio if mode == 'contain' else Qt.KeepAspectRatioByExpanding)
        scaled = source if mode == 'center' else source.scaled(canvas.size(), ratio, Qt.SmoothTransformation)
        painter.drawPixmap((canvas.width()-scaled.width())//2,
                           (canvas.height()-scaled.height())//2, scaled)
    painter.end()
    return canvas
