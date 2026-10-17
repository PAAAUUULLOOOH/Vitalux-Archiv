"""Headless smoke test for the standalone GPU-native Qt Quick prototype."""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QSG_RHI_BACKEND", "software")

from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickView

from vitalux.gpu_ui import Telemetry, create_view, _percent


def run():
    app = QGuiApplication.instance() or QGuiApplication([])
    bridge = Telemetry("openSUSE Tumbleweed")
    assert bridge.metrics["status"].startswith("Warte")
    assert _percent(None) == 0.0
    assert _percent(150) == 100.0
    assert _percent(float("nan")) == 0.0

    bridge.accept_sample({
        "cpu": {"model": "Test CPU", "usage": 48.7, "temp": 63},
        "ram": {"total": 17179869184, "used": 8589934592, "percent": 50},
        "gpus": [{"name": "Test Radeon", "usage": 37, "temp": 55, "clock": 2500}],
        "net": {"down": 1048576, "up": 524288},
        "uptime": 3750,
    })
    data = bridge.metrics
    assert data["cpuModel"] == "Test CPU"
    assert data["gpuModel"] == "Test Radeon"
    assert data["cpuUsage"] == 48.7
    assert data["gpuUsage"] == 37
    assert data["ramUsed"] == "8.0 GiB"
    assert data["netDown"] == "1.00 MiB/s"
    assert data["uptime"] == "1 h 02 min"
    assert data["cpuHistory"][-1] == 48.7

    view = create_view(bridge)
    assert isinstance(view, QQuickView)
    assert view.status() == QQuickView.Ready, [str(x) for x in view.errors()]
    assert view.rootObject() is not None
    assert view.rootObject().property("currentPage") == 0
    view.rootObject().setProperty("currentPage", 6)
    assert view.rootObject().property("currentPage") == 6
    app.processEvents()
    view.close()
    print("Native QQuickView live telemetry and QML preview: OK")


if __name__ == "__main__":
    run()
