import os
import subprocess

from PySide6.QtCore import QObject, QThread, QTimer, Signal

from . import updater
from .i18n import tr


class _CheckThread(QThread):
    done = Signal(object)

    def __init__(self, parent):
        super().__init__(parent)

    def run(self):
        try:
            self.done.emit(updater.check())
        except Exception as exc:
            self.done.emit({"ok": False, "error": str(exc)})


class _InstallThread(QThread):
    progress = Signal(float)
    done = Signal(str)          # leer = Erfolg, sonst Fehlertext

    def __init__(self, url, sha256, parent):
        super().__init__(parent)
        self.url, self.sha256 = url, sha256
        self.pending_path = None

    def run(self):
        try:
            self.pending_path = updater.install(self.url, sha256=self.sha256, progress=self.progress.emit)
            self.done.emit("")
        except Exception as exc:
            self.done.emit(f"{tr('Installation fehlgeschlagen:')} {exc}")


class _RestoreThread(QThread):
    done = Signal(str)

    def run(self):
        try:
            updater.restore_previous()
            self.done.emit('')
        except Exception as exc:
            self.done.emit(str(exc))


class UpdateManager(QObject):
    """Hält den Update-Status. Bleibt bestehen, auch wenn die Oberfläche (z. B. bei Sprachwechsel) neu aufgebaut wird."""
    changed = Signal()
    progress = Signal(float)
    restart = Signal()

    def __init__(self):
        super().__init__()
        self.status = "idle"      # idle, checking, uptodate, available, error, installing, installed
        self.latest = self.notes = self.url = self.error = self.sha256 = ""
        self.pending_path = None
        self._thread = None
        self._active_threads = []  # Do not destroy Qt threads while queued signals are still finishing.
        self._timer = QTimer(self)
        self._timer.setInterval(6 * 3600 * 1000)       # alle 6 Stunden prüfen
        self._timer.timeout.connect(self.check)
        self._timer.start()

    @property
    def available(self):
        return self.status == "available"

    def _start_worker(self, worker):
        self._thread = worker
        self._active_threads.append(worker)
        worker.finished.connect(lambda w=worker: self._active_threads.remove(w)
                                if w in self._active_threads else None)
        worker.start()

    def check(self):
        if self.status in ("checking", "installing"):
            return
        self.status = "checking"
        self.error = ""
        self.changed.emit()
        thread = _CheckThread(self)
        thread.done.connect(self._on_checked)
        self._start_worker(thread)

    def _on_checked(self, res):
        if res.get("ok"):
            self.latest, self.notes, self.url, self.sha256 = res["latest"], res["notes"], res["url"], res["sha256"]
            self.status = "available" if res["newer"] else "uptodate"
        else:
            self.latest = self.notes = self.url = self.sha256 = ""
            self.status, self.error = "error", res.get("error", "Updateprüfung fehlgeschlagen")
        self.changed.emit()

    def install(self):
        if self.status != "available" or not self.url:
            return
        self.status = "installing"
        self.changed.emit()
        thread = _InstallThread(self.url, self.sha256, self)
        thread.progress.connect(self.progress)
        thread.done.connect(self._on_installed)
        self._start_worker(thread)

    def _on_installed(self, err):
        if err:
            self.status, self.error = "error", err
            self.changed.emit()
            return
        self.pending_path = getattr(self._thread, 'pending_path', None)
        self.status = "installed"
        self.changed.emit()
        QTimer.singleShot(900, self._restart)

    def rollback(self):
        if updater.appimage_path() or self.status in ('checking', 'installing') or not updater.backup_available():
            return
        self.status = 'installing'
        self.changed.emit()
        thread = _RestoreThread(self)
        thread.done.connect(self._on_installed)
        self._start_worker(thread)

    def _restart(self):
        if self.pending_path:
            try:
                updater.activate_appimage_update(self.pending_path)
            except Exception as exc:
                self.status, self.error = 'error', str(exc)
                self.changed.emit()
                return
        else:
            root = updater.app_root()
            subprocess.Popen(["bash", os.path.join(root, "run.sh")], cwd=root, start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.restart.emit()

    def shutdown(self):
        for thread in list(self._active_threads):
            if thread.isRunning():
                thread.wait(10000)
