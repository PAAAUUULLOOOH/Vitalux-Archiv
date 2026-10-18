"""Offline, read-only Vitalux hardware monitoring regressions."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile

from vitalux.monitor_insights import (
    SessionExtrema, format_range, hardware_status,
    pcie_link, report_data, report_text, write_report, valid_number,
)


def sample():
    return {
        "cpu": {"usage": 14.0, "temp": 42.1, "model": "CPU"},
        "ram": {"percent": 53.0},
        "gpus": [{"name": "AMD Radeon RX 9070 XT", "usage": 26.0,
                  "temp": 49.0, "clock": 1825.0, "power": 72.0,
                  "vram_total": 17179869184, "vram_used": 2147483648}],
        "disks": [{"mount": "/", "percent": 78.0}],
    }


def test_min_max():
    counter = SessionExtrema()
    s = sample()
    counter.update(s)
    assert format_range(counter.snapshot(), "gpu_clock", "MHz") == "1825–1825 MHz"
    s["cpu"]["temp"] = None
    s["gpus"][0]["temp"] = 51
    counter.update(s)
    assert counter.snapshot()["cpu_temp"] == [42.1, 42.1]
    assert counter.snapshot()["gpu_temp"] == [49.0, 51]
    assert not valid_number(float("nan"))
    assert not valid_number(True)
    counter.reset()
    assert counter.snapshot() == {}


def test_pcie():
    assert pcie_link("16.0 GT/s PCIe", "16", "32.0 GT/s PCIe", "16") == (
        "16.0 GT/s PCIe · x16", "32.0 GT/s PCIe · x16")
    assert pcie_link(None, None, None, None) == ("–", "–")


def test_hardware_status():
    s = sample()
    result = dict(hardware_status(s, {"cpu_temp": 65, "gpu_temp": 48,
                                      "ram_usage": 90, "disk_usage": 95}))
    assert result["GPU"].startswith("Warnwert erreicht:")
    assert result["Systemlaufwerk"] == "78% belegt"
    s["gpus"] = []
    assert dict(hardware_status(s))["GPU"] == "Nicht verfügbar"


def test_report_formats():
    s = sample()
    report = report_data(s, {"mesa": "26.2", "board": "ASUS"}, "test", {"cpu_temp": [42, 51]})
    assert "ASUS" in report_text(report)
    with tempfile.TemporaryDirectory() as base:
        p_txt, p_json = Path(base) / "report.txt", Path(base) / "report.json"
        write_report(p_txt, report)
        write_report(p_json, report)
        assert "Vitalux" in p_txt.read_text()
        assert json.loads(p_json.read_text())["sample"]["cpu"]["temp"] == 42.1
        try:
            write_report(Path(base) / "bad.log", report)
        except ValueError:
            pass
        else:
            raise AssertionError("Unsupported file types must be rejected")


if __name__ == "__main__":
    test_min_max()
    test_pcie()
    test_hardware_status()
    test_report_formats()
    print("Read-only GPU, motherboard, PCIe, history and export: PASS")
