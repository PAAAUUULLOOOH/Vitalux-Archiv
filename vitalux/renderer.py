"""Opt-in OpenGL renderer selection with startup recovery.

This is deliberately an experiment: Qt raster widgets continue to paint on
the CPU. The OpenGL background and Qt's final top-level composition use a
GL context when the platform can provide one.
"""
import os

from . import settings

SOFTWARE = 'software'
OPENGL = 'opengl'
_failure = ''


def desired():
    forced = os.environ.get('VITALUX_RENDERER', '').strip().lower()
    if forced in (SOFTWARE, OPENGL):
        return forced
    saved = settings.get('render_backend', SOFTWARE)
    return saved if saved in (SOFTWARE, OPENGL) else SOFTWARE


def prepare_start():
    """Recover from a crash during a previous GPU-mode startup.

    This boot marker is cleared shortly after the GUI starts successfully.
    The environment override always permits an emergency CPU-only launch.
    """
    global _failure
    if os.environ.get('VITALUX_RENDERER', '').strip().lower() == SOFTWARE:
        return SOFTWARE
    if desired() != OPENGL:
        return SOFTWARE
    if settings.get('gpu_boot_pending', False):
        _failure = 'Der vorherige OpenGL-Start wurde nicht abgeschlossen. CPU-Rendering wurde zur Sicherheit wieder aktiviert.'
        settings.set('render_backend', SOFTWARE)
        settings.set('gpu_boot_pending', False)
        return SOFTWARE
    settings.set('gpu_boot_pending', True)
    return OPENGL


def successful_start():
    if settings.get('gpu_boot_pending', False):
        settings.set('gpu_boot_pending', False)


def gpu_available():
    """Probe an actual offscreen GL context before selecting QOpenGLWidget."""
    if os.environ.get('QT_QPA_PLATFORM', '').lower() in ('offscreen', 'minimal'):
        return False
    try:
        from PySide6.QtOpenGLWidgets import QOpenGLWidget  # noqa: F401
        from PySide6.QtGui import QOffscreenSurface, QOpenGLContext
        surface = QOffscreenSurface()
        surface.create()
        if not surface.isValid():
            return False
        context = QOpenGLContext()
        if not context.create() or not context.makeCurrent(surface):
            return False
        context.doneCurrent()
        return True
    except (ImportError, RuntimeError, OSError):
        return False


def fallback():
    global _failure
    _failure = 'OpenGL ist mit dieser Sitzung oder den Grafiktreibern nicht verfügbar. CPU-Rendering bleibt aktiv.'
    if os.environ.get('VITALUX_RENDERER', '').strip().lower() != OPENGL:
        settings.set('render_backend', SOFTWARE)
    successful_start()


def warning():
    return _failure
