"""Qt Quick fallback and true scene-graph GPU path, plus Info page credit."""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, os.getcwd())

from PySide6.QtWidgets import QApplication, QLabel
from vitalux import renderer, settings, theme, i18n
from vitalux.glass import AmbientScene, create_ambient_scene
from vitalux.pages_extra import InfoPage
from vitalux.i18n import tr

GPU = os.environ.get('VITALUX_QUICK_SMOKE') == '1'


def run():
    app = QApplication.instance() or QApplication([])
    original_path = settings.PATH
    original_lang = i18n.lang()
    with tempfile.TemporaryDirectory(prefix='vitalux-quick-') as tmp:
        try:
            settings.PATH = str(Path(tmp) / 'settings.json')
            theme.set_mode('glass')
            settings.set('render_backend', renderer.QTQUICK)
            renderer.prepare_start()
            if GPU:
                assert renderer.quick_available(), 'Qt Quick modules or GL context missing'
                from PySide6.QtQuickWidgets import QQuickWidget
                from PySide6.QtQuick import QSGRendererInterface
                widget = create_ambient_scene()
                assert isinstance(widget, QQuickWidget), type(widget).__name__
                assert widget.render_backend == renderer.QTQUICK
                assert widget.rootObject() is not None
                widget.resize(520, 340)
                sample = QLabel('Qt widget over Qt Quick texture', widget)
                sample.move(30, 30)
                sample.show()
                widget.show()
                for _ in range(24):
                    app.processEvents()
                renderer_type = widget.quickWindow().rendererInterface().graphicsApi()
                assert renderer_type == QSGRendererInterface.OpenGL, renderer_type
                assert not widget.grabFramebuffer().isNull(), 'Qt Quick framebuffer empty'
                before = widget._generation
                widget.sync_background()
                for _ in range(8):
                    app.processEvents()
                assert widget._generation > before, 'QML did not receive a wallpaper update'
                assert widget.rootObject().property('generation') == widget._generation
                assert sample.isVisible()
                widget.close()
                renderer.successful_start()
                print('GPU Qt Quick scene graph and QWidget composition: OK')
            else:
                assert not renderer.quick_available(), 'Headless Quick should be disabled'
                widget = create_ambient_scene()
                assert isinstance(widget, AmbientScene)
                assert settings.get('render_backend') == renderer.SOFTWARE
                widget.close()
                print('CPU fallback when Qt Quick GPU is unavailable: OK')

            theme.set_mode('glass')
            app.setStyleSheet(theme.stylesheet())
            info = InfoPage({'name': 'openSUSE'})
            info.show()
            app.processEvents()
            credit = info.findChild(QLabel, 'supportCredit')
            author = info.findChild(QLabel, 'madeBy')
            assert credit is not None and author is not None
            from PySide6.QtCore import Qt
            from vitalux.pages_extra import CREDIT_TEXT, CREDIT_URL
            from vitalux.ui_locale import retranslate_widgets
            assert credit is info.support_credit
            assert credit.textFormat() == Qt.RichText
            assert credit.openExternalLinks()
            assert credit.textInteractionFlags() & Qt.LinksAccessibleByMouse
            assert credit.text().startswith('<b>Danke an:</b> ')
            assert credit.text().count('<a href=') == 1
            assert f'<a href="{CREDIT_URL}"' in credit.text()
            assert 'TimBooH</a>' in credit.text()
            assert 'der Integration eigener Hintergrundbilder' in credit.text()
            assert 'OpenGL/CPU-Rendering' in credit.text()
            assert credit.accessibleName() == CREDIT_TEXT
            assert credit.font().pixelSize() < author.font().pixelSize(), (
                credit.font().pixelSize(), author.font().pixelSize())
            i18n.set_lang('en')
            retranslate_widgets(info)
            assert credit.text().startswith('<b>Thanks to:</b> ')
            assert f'<a href="{CREDIT_URL}"' in credit.text()
            assert credit.accessibleName() == tr(CREDIT_TEXT)
            i18n.set_lang('de')
            retranslate_widgets(info)
            assert credit.text().startswith('<b>Danke an:</b> ')
            info.close()
        finally:
            settings.PATH = original_path
            i18n.set_lang(original_lang)


if __name__ == '__main__':
    run()
