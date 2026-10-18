"""Real Qt offscreen smoke for integrated Vitalux Insights and focus window."""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.getcwd())

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
try:
    from PySide6.QtTest import QTest
except ImportError:
    # Portable runtime ships the Qt desktop widgets, but not QtTest.
    QTest = None
from vitalux import theme
from vitalux.insight_engine import MonitoringLab
from vitalux.insight_ui import FocusWindow, _HardwareNode
from vitalux.pages import GpuPage


def sample(gpu_usage=40, ram_usage=48):
    return {"cpu": {"model": "i5-14600KF", "usage": 55, "temp": 62},
            "ram": {"percent": ram_usage, "total": 32000000000, "used": 16000000000},
            "gpus": [{"name": "Radeon RX 9070 XT", "driver": "amdgpu", "vendor": "AMD",
                      "usage": gpu_usage, "clock": 2100, "clock_mem": 1250,
                      "temp": 51, "hotspot": 65, "voltage": 900, "power": 160,
                      "vram_total": 16000000000, "vram_used": 5000000000,
                      "pcie_current": "16.0 GT/s · x16"}],
            "disks": [{"mount": "/", "percent": 54}],
            "session_extrema": {}}


def check_lab_panel():
    app = QApplication.instance() or QApplication([])
    theme.set_mode("glass")
    app.setStyleSheet(theme.stylesheet())
    lab = MonitoringLab()
    focus_requests = []
    page = GpuPage(lab, lambda: focus_requests.append("open"))
    page.resize(1120, 800)
    page.show()
    for value in (30, 40, 60):
        sample_data = sample(value)
        lab.ingest(sample_data)
    page.refresh(sample_data, {"gpu": [30, 40, 60], "vram": [33, 33, 33],
                               "gpu_temp": [48, 50, 51], "gpu_clock": [1900, 2000, 2100]})
    app.processEvents()
    panel = page.lab_panel
    assert panel is not None
    assert not panel.record_group.isVisible()
    assert "GPU-Auslastung" not in panel.findings.text() or panel.findings.text()
    panel.focus.click()
    assert focus_requests == ["open"]
    panel.show_advanced.click()
    app.processEvents()
    assert panel.record_group.isVisible()
    assert panel.compare_group.isVisible()
    assert panel.trend_group.isVisible()
    assert panel.trend_chart.graph.mode == "percent"
    assert len(panel.trend_chart.toggles) == 3
    assert panel.map.scene().items()
    nodes = [node for node in panel.map.scene().items() if isinstance(node, _HardwareNode)]
    assert {node.key for node in nodes} == {"cpu", "gpu", "ram", "disk", "mainboard"}
    node = next(x for x in nodes if x.key == "mainboard")
    point = panel.map.mapFromScene(node.mapToScene(node.rect().center()))
    if QTest is not None:
        QTest.mouseClick(panel.map.viewport(), Qt.LeftButton, pos=point)
    else:
        node.callback(node.key)  # Native item's wired click handler
    assert "Mainboard" in panel.hardware_detail.text()

    panel.session_name.setText("Cyberpunk")
    panel.begin.click()
    assert lab.started is not None
    for value in (70, 90, 99):
        s = sample(value)
        lab.ingest(s)
        page.refresh(s, {"gpu": [value], "vram": [33],
                         "gpu_temp": [51], "gpu_clock": [2100]})
    panel.end.click()
    assert lab.last_session and lab.last_session["samples"] == 3
    assert "Cyberpunk" in panel.session_report.text()
    panel.before.click()
    s2 = sample(55)
    lab.ingest(s2)
    page.refresh(s2, {"gpu": [55], "vram": [33], "gpu_temp": [51], "gpu_clock": [2100]})
    panel.after.click()
    assert lab.comparison()
    assert "GPU" in panel.comparison.text()
    assert panel.timeline.count() >= 1
    panel.timeline.setCurrentRow(0)
    assert "GPU" in panel.event_detail.text()

    focus = FocusWindow()
    focus.show()
    focus.update_sample(s2)
    app.processEvents()
    assert "55.0" in focus.entries[0][1].text()
    focus.entries[0][0].setCurrentIndex(focus.entries[0][0].findData("cpu_temp"))
    focus.update_sample(s2)
    assert "62.0" in focus.entries[0][1].text()
    from vitalux import i18n
    i18n.set_lang("en")
    panel.retranslate()
    focus.retranslate()
    assert panel.compare_group.title() == "Before / after comparison"
    assert "Focus mode" in focus.windowTitle()
    assert "DRIVES" in [node.text.text() for node in nodes]
    i18n.set_lang("de")
    panel.retranslate()
    focus.retranslate()
    focus.close()
    page.close()
    app.processEvents()
    print("Native Insights, gaming, comparison, hardware nodes and focus mode: PASS")


if __name__ == "__main__":
    check_lab_panel()
