"""Native Qt Quick prototype for Vitalux, separate from the stable Qt Widgets UI.

Launch explicitly with run.sh --gpu-preview (or python -m vitalux.gpu_ui).
No QQuickWidget embedding: the QQuickView owns its scene graph, including
cards, scrolling, text and graph bars. The regular application is unchanged.
"""
import math
import os
import sys
from collections import deque
from pathlib import Path

from PySide6.QtCore import QObject, Property, QThread, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQuick import QQuickView

from . import APP_NAME, distro, sensors, settings, theme
from .wallpaper_accents import resolve_accent


_ROOT = Path(__file__).resolve().parents[1]
_QML = _ROOT / "assets" / "quick-ui" / "Main.qml"


def _number(value, fallback=0.0):
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else fallback
    except (ValueError, TypeError, OverflowError):
        return fallback


def _percent(value):
    return max(0.0, min(100.0, _number(value)))


def _gib(value):
    return f"{_number(value) / 1073741824:.1f} GiB"


class SampleWorker(QThread):
    sampleReady = Signal(object)

    def run(self):
        while not self.isInterruptionRequested():
            try:
                self.sampleReady.emit(sensors.collect())
            except Exception as exc:
                self.sampleReady.emit({"error": str(exc)})
            # Sensor polling is intentionally independent from render frames.
            for _ in range(10):
                if self.isInterruptionRequested():
                    break
                self.msleep(100)


class Telemetry(QObject):
    metricsChanged = Signal()
    paletteChanged = Signal()

    def __init__(self, system_name="Linux", parent=None):
        super().__init__(parent)
        self._cpu_history = deque(maxlen=56)
        self._metrics = {
            "cpuUsage": 0.0, "ramUsage": 0.0, "gpuUsage": 0.0,
            "cpuModel": "–", "gpuModel": "–", "cpuTemp": "–",
            "gpuTemp": "–", "gpuClock": "–", "uptime": "–",
            "ramUsed": "–", "ramTotal": "–", "netDown": "–",
            "netUp": "–", "kernel": os.uname().release,
            "system": system_name, "cpuHistory": [0.0] * 56,
            "status": "Warte auf die erste Sensormessung…",
        }
        self._palette = {
            "bg": theme.BG, "sidebar": theme.SIDEBAR,
            "card": theme.CARD, "border": theme.BORDER,
            "text": theme.TEXT, "muted": theme.MUTED,
            "accent": theme.accent(),
        }

    @Property("QVariantMap", notify=metricsChanged)
    def metrics(self):
        return self._metrics

    @Property("QVariantMap", notify=paletteChanged)
    def palette(self):
        return self._palette

    @Slot(object)
    def accept_sample(self, data):
        if not isinstance(data, dict) or "error" in data:
            self._metrics = {**self._metrics, "status":
                             "Messfehler: " + str(data.get("error", "Ungültige Messung"))
                             if isinstance(data, dict) else "Ungültige Messung"}
            self.metricsChanged.emit()
            return
        cpu = data.get("cpu") or {}
        ram = data.get("ram") or {}
        gpus = data.get("gpus") or []
        gpu = gpus[0] if gpus and isinstance(gpus[0], dict) else {}
        net = data.get("net") or {}
        cpu_pct = _percent(cpu.get("usage"))
        self._cpu_history.append(cpu_pct)
        uptime_s = max(0, int(_number(data.get("uptime"))))
        hours, minutes = divmod(uptime_s // 60, 60)
        self._metrics = {
            "cpuUsage": cpu_pct,
            "ramUsage": _percent(ram.get("percent")),
            "gpuUsage": _percent(gpu.get("usage")),
            "cpuModel": str(cpu.get("model") or "Nicht erkannt"),
            "gpuModel": str(gpu.get("name") or "Keine GPU-Messwerte"),
            "cpuTemp": f"{_number(cpu['temp']):.0f} °C" if cpu.get("temp") is not None else "–",
            "gpuTemp": f"{_number(gpu['temp']):.0f} °C" if gpu.get("temp") is not None else "–",
            "gpuClock": f"{_number(gpu['clock']):.0f} MHz" if gpu.get("clock") is not None else "–",
            "uptime": f"{hours} h {minutes:02d} min",
            "ramUsed": _gib(ram.get("used")),
            "ramTotal": _gib(ram.get("total")),
            "netDown": f"{_number(net.get('down')) / 1048576:.2f} MiB/s",
            "netUp": f"{_number(net.get('up')) / 1048576:.2f} MiB/s",
            "kernel": os.uname().release,
            "system": self._metrics["system"],
            "cpuHistory": list(self._cpu_history),
            "status": "Live · Messung jede Sekunde",
        }
        self.metricsChanged.emit()


def create_view(telemetry):
    if not _QML.is_file():
        raise RuntimeError(f"Qt Quick preview fehlt: {_QML}")
    view = QQuickView()
    view.setColor(theme.BG)
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.rootContext().setContextProperty("telemetry", telemetry)
    view.setSource(QUrl.fromLocalFile(str(_QML)))
    if view.status() != QQuickView.Ready or view.rootObject() is None:
        messages = "; ".join(error.toString() for error in view.errors())
        raise RuntimeError("QML konnte nicht geladen werden: " + messages)
    view.setTitle(APP_NAME + " – Qt Quick GPU-Vorschau (experimentell)")
    view.setMinimumSize(QQuickView().minimumSize()) if False else None
    view.resize(1250, 850)
    view.setIcon(QIcon(str(_ROOT / "assets" / "vitalux.svg")))
    return view


def main():
    # This preview never writes render_backend or changes the stable UI.
    os.environ.setdefault("QSG_RHI_BACKEND", "opengl")
    app = QGuiApplication(sys.argv)
    app.setApplicationName(APP_NAME + " GPU-Vorschau")
    try:
        info = distro.info()
        theme.set_mode(settings.get("theme", "glass"))
        theme.set_accent(resolve_accent(settings.get("accent", "#4f8cff"),
                                        info.get("color", "#4f8cff")))
        telemetry = Telemetry(info.get("name", "Linux"))
        view = create_view(telemetry)
    except Exception as exc:
        print(f"Vitalux Qt Quick GPU-Vorschau: {exc}", file=sys.stderr)
        return 2

    sensors.prime()
    worker = SampleWorker()
    worker.sampleReady.connect(telemetry.accept_sample)
    view.show()
    worker.start()

    def stop():
        worker.requestInterruption()
        worker.wait(5000)

    app.aboutToQuit.connect(stop)
    code = app.exec()
    stop()
    return code


if __name__ == "__main__":
    sys.exit(main())
