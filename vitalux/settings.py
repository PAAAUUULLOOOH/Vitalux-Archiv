"""Atomic, cached per-user preferences. Reads follow external file changes."""
import copy
import json
import os
import tempfile
import warnings

from . import APP_ID

PATH = os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"),
                    APP_ID, "settings.json")
_cache_identity = None
_cache_value = None


def _identity():
    try:
        info = os.stat(PATH)
        return (PATH, info.st_mtime_ns, info.st_size, info.st_ino)
    except OSError:
        return (PATH, None, None, None)


def _load():
    global _cache_identity, _cache_value
    identity = _identity()
    if identity == _cache_identity and _cache_value is not None:
        return copy.deepcopy(_cache_value)
    try:
        with open(PATH, encoding="utf-8") as f:
            data = json.load(f)
            data = data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        data = {}
    _cache_identity, _cache_value = identity, data
    return copy.deepcopy(data)


def get(key, default=None):
    return _load().get(key, default)


def get_many(defaults):
    """Read several settings using just one snapshot of the settings file."""
    if not isinstance(defaults, dict):
        raise TypeError("Preferences defaults must be a dictionary")
    data = _load()
    return {key: data.get(key, default) for key, default in defaults.items()}


def _report_write_error(exc):
    message = f"Vitalux konnte die Einstellungen nicht speichern: {exc}"
    warnings.warn(message, RuntimeWarning, stacklevel=2)
    try:
        # Error dialogs are allowed on the Qt GUI thread only.
        from PySide6.QtWidgets import QApplication, QMessageBox
        from PySide6.QtCore import QThread
        app = QApplication.instance()
        if app is not None and QThread.currentThread() == app.thread():
            QMessageBox.warning(app.activeWindow(), "Vitalux – Einstellungen", message)
    except (ImportError, RuntimeError):
        pass


def set(key, value):
    """Update one preference using the shared atomic writer."""
    return set_many({key: value})


def set_many(changes):
    """Save multiple preferences with one fsync/replace and one cache update.

    A no-op update skips disk writes only if a preferences file already exists.
    The caller-owned values are copied so later mutation cannot alter the cache.
    """
    global _cache_identity, _cache_value
    if not isinstance(changes, dict):
        raise TypeError("Preferences changes must be a dictionary")
    if not changes:
        return True
    data = _load()
    if os.path.isfile(PATH) and all(key in data and data[key] == value
                                    for key, value in changes.items()):
        return True
    data.update(copy.deepcopy(changes))
    temporary = None
    try:
        parent = os.path.dirname(PATH)
        os.makedirs(parent, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".settings-", suffix=".tmp", dir=parent)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, PATH)
        temporary = None
        _cache_identity, _cache_value = _identity(), copy.deepcopy(data)
        return True
    except OSError as exc:
        _report_write_error(exc)
        return False
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except OSError:
                pass
