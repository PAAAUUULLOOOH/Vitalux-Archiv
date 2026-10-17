"""Native Qt renderer regression: stable raster fallback and OpenGL smoke.

Set VITALUX_GL_SMOKE=1 under Xvfb/Mesa to exercise a real GL framebuffer.
The test intentionally makes no GPU speed claim: Mesa may be software GL.
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.getcwd())
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
from vitalux import renderer, settings
from vitalux.glass import AmbientScene, create_ambient_scene

GL_SMOKE = os.environ.get('VITALUX_GL_SMOKE') == '1'


def run():
    app = QApplication.instance() or QApplication([])
    before = settings.PATH
    with tempfile.TemporaryDirectory(prefix='vitalux-gl-check-') as directory:
        try:
            settings.PATH = str(Path(directory) / 'settings.json')
            settings.set('render_backend', renderer.SOFTWARE)
            plain = create_ambient_scene()
            assert isinstance(plain, AmbientScene)
            assert plain.render_backend == renderer.SOFTWARE
            plain.resize(300, 210)
            plain.show()
            app.processEvents()
            assert not plain.grab().isNull()
            plain.close()

            if GL_SMOKE:
                from PySide6.QtOpenGLWidgets import QOpenGLWidget
                os.environ.pop('VITALUX_RENDERER', None)
                settings.set('render_backend', renderer.OPENGL)
                assert renderer.gpu_available(), 'No OpenGL context: Mesa/Xvfb is not working'
                renderer.prepare_start()
                scene = create_ambient_scene()
                assert isinstance(scene, QOpenGLWidget)
                assert scene.render_backend == renderer.OPENGL
                scene.resize(440, 300)
                layout = QVBoxLayout(scene)
                text = QLabel('GPU compositor and raster child', scene)
                text.setAttribute(Qt.WA_TransparentForMouseEvents, True)
                layout.addWidget(text)
                scene.show()
                for _ in range(15):
                    app.processEvents()
                assert scene.context() is not None and scene.context().isValid()
                assert not scene.grab().isNull(), 'GPU background did not paint'
                scene.close()
                renderer.successful_start()
                assert not settings.get('gpu_boot_pending', False)
                print('Qt OpenGL-backed scene and child widgets: OK')
            else:
                # Even with the stored GPU option, headless/offscreen must return
                # to the CPU instead of constructing an invalid OpenGL widget.
                settings.set('render_backend', renderer.OPENGL)
                settings.set('gpu_boot_pending', False)
                renderer.prepare_start()
                assert renderer.gpu_available() is False
                fallback = create_ambient_scene()
                assert isinstance(fallback, AmbientScene)
                assert fallback.render_backend == renderer.SOFTWARE
                assert settings.get('render_backend') == renderer.SOFTWARE
                assert not settings.get('gpu_boot_pending', False)
                fallback.close()
                # Interruption during the initial GPU boot gets rolled back.
                settings.set('render_backend', renderer.OPENGL)
                settings.set('gpu_boot_pending', True)
                assert renderer.prepare_start() == renderer.SOFTWARE
                assert settings.get('render_backend') == renderer.SOFTWARE
                print('CPU raster fallback and interrupted-GPU-start recovery: OK')
        finally:
            settings.PATH = before


if __name__ == '__main__':
    run()
