"""Native Qt GPU/mainboard monitoring smoke tests. No GPU access required."""
from __future__ import annotations
import os
import sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.getcwd())

from PySide6.QtWidgets import QApplication
from vitalux import theme
from vitalux.pages import GpuPage, CpuPage, SystemPage, GpuCard
from vitalux.widgets import ChartPanel


def gpu():
    return dict(vendor="AMD", name="Radeon RX 9070 XT", driver="amdgpu",
                usage=27, vram_total=17179869184, vram_used=2147483648,
                clock=1700, clock_mem=1240, temp=48, hotspot=63,
                power=81, fan=25, fan_rpm=900, voltage=870,
                pcie_current="16.0 GT/s PCIe · x16",
                pcie_max="32.0 GT/s PCIe · x16",
                sensor_source="Linux DRM / sysfs")


def sample():
    return {"gpus": [gpu()],
            "motherboard": {"temperature": 34, "source": "nct · System temp"},
            "session_extrema": {"gpu_temp": [32, 60], "cpu_temp": [40, 70],
                                "board_temp": [28, 38]}}


def check_gui():
    app = QApplication.instance() or QApplication([])
    theme.set_mode("glass")
    app.setStyleSheet(theme.stylesheet())
    page = GpuPage()
    page.show()
    h = {"gpu": [14, 27], "vram": [8, 12.5],
         "gpu_temp": [41, 48], "gpu_clock": [1100, 1700]}
    page.refresh(sample(), h)
    app.processEvents()
    assert len(page.cards) == 1
    card = page.cards[0]
    assert card.kv["GPU-Takt"].v.text() == "1700 MHz"
    assert card.kv["Spannung"].v.text() == "870 mV"
    assert card.kv["PCIe aktuell"].v.text().endswith("x16")
    assert "32.0 GT/s" in card.kv["PCIe maximal"].v.text()
    assert card.kv["Mesa"].v.text() != ""
    assert not card.details.isVisible()
    card.more_btn.click()
    app.processEvents()
    assert card.details.isVisible()
    assert card.temperature_graph.graph.mode == "temperature"
    assert card.clock_graph.graph.mode == "clock"
    assert not hasattr(page, "tuning")
    missing = gpu()
    missing.update(voltage=None, temp=None, power=None)
    page.refresh({**sample(), "gpus": [missing]}, h)
    assert card.kv["Spannung"].v.text() != "0 mV"
    assert card.kv["Temperatur"].v.text() != "0 °C"

    system = SystemPage({"name": "Linux", "color": "#52d3ff"})
    system.show()
    system.refresh({"gpus": [gpu()], "cpu": {"model": "CPU"},
                    "uptime": 100, "app_resources": {},
                    "ram": {"percent": 50}, "disks": [{"mount": "/", "percent": 40}],
                    "session_extrema": {}}, {})
    assert not hasattr(system, "board_card"), "Separate motherboard section must be gone"
    assert system.status_rows["GPU"].v.text()
    system.close()
    page.close()
    app.processEvents()
    print("Read-only GPU details, removal of board panel and hardware status Qt smoke: PASS")


if __name__ == "__main__":
    check_gui()
