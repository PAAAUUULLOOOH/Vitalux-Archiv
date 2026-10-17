"""Regression checks for tray values and personal wallpapers."""
import os
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, os.getcwd())

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication
from vitalux import settings, theme, backdrops, user_background
from vitalux.tray_preview import tray_tooltip, TrayPreview
from vitalux.glass import AmbientScene


def run():
    app = QApplication.instance() or QApplication([])
    original = settings.PATH
    with tempfile.TemporaryDirectory() as tmp:
        try:
            settings.PATH = os.path.join(tmp, 'settings.json')
            theme.set_mode('glass')
            sample = {'cpu': {'usage': 21.0, 'temp': 53},
                      'gpus': [{'usage': 62, 'temp': 70}],
                      'ram': {'percent': 42}}
            tooltip = tray_tooltip(sample)
            assert 'CPU 21%' in tooltip and 'GPU 62%' in tooltip
            assert 'RAM 42%' in tooltip and '53 °C' in tooltip
            assert '–' in tray_tooltip({'gpus': []})
            preview = TrayPreview()
            preview.update_sample(sample)
            assert preview.values['GPU'].text() == '62%'
            preview.close()

            source = Path(tmp) / 'test.png'
            image = QImage(12, 6, QImage.Format_RGB32)
            image.fill(QColor('#ef4444'))
            assert image.save(str(source))
            entry = user_background.import_image(source)
            assert user_background.image_path(entry['file']).is_file()
            settings.set('custom_backgrounds', [entry])
            settings.set('custom_background_selected', entry['file'])
            settings.set('background_style', 'custom_image')
            assert len(user_background.images()) == 1
            assert backdrops.resolve('custom_image', 'glass') == 'custom_image'
            for fit in ('cover', 'contain', 'stretch', 'center', 'tile'):
                settings.set('custom_background_fit', fit)
                assert user_background.draw(QSize(240, 140), entry['file'], fit).size() == QSize(240, 140)
                scene = AmbientScene()
                scene.resize(240, 140)
                scene.show()
                app.processEvents()
                assert scene.sharp_backdrop().size() == QSize(240, 140)
                scene.close()
            user_background.image_path(entry['file']).unlink()
            assert user_background.images() == []
        finally:
            settings.PATH = original


if __name__ == '__main__':
    run()
    print('Custom wallpaper and tray tests passed')
