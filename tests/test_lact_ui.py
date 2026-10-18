"""LACT native Qt panel smoke test, using a fake daemon (no GPU writes)."""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.getcwd())

from PySide6.QtWidgets import QApplication
from vitalux import theme
from vitalux.lact_ui import LactTuningCard
from vitalux.lact_client import LactError


class FakeLact:
    def __init__(self):
        self.config = {
            "power_cap": 250.0,
            "performance_level": "auto",
            "fan_control_enabled": False,
            "gpu_clock_offsets": {"0": 200},
            "fan_control_settings": {
                "mode": "curve", "static_speed": 0.5,
                "curve": {"40": 0.3, "50": 0.35, "60": 0.5,
                          "70": 0.75, "80": 1.0},
            },
        }
        self.switched = []

    def devices(self):
        return [{"id": "gpu-1", "name": "AMD Radeon RX 9070 XT"}]

    def gpu_config(self, gpu_id):
        assert gpu_id == "gpu-1"
        return self.config.copy()

    def device_stats(self, _):
        return {
            "power": {"cap_min": 200.0, "cap_max": 300.0, "cap_current": 250.0,
                      "average": 55.0},
            "fan": {"speed_max": 3000, "speed_current": 896, "temperature_key": "edge"},
            "clockspeed": {"gpu_clockspeed": 167, "vram_clockspeed": 1258},
            "voltage": {"gpu": 552},
            "temps": {"edge": {"current": 42.0, "display_only": False},
                      "junction": {"current": 45.0, "display_only": False}},
            "busy_percent": 3,
        }

    def device_clocks(self, _):
        return {"table": {"type": "amd", "value": {
            "kind": "rdna", "data": {
                "sclk_offset": 200,
                "od_range": {"sclk_offset": {"min": -500, "max": 1000},
                             "voltage_offset": {"min": -200, "max": 0},
                             "mclk": {"min": 97, "max": 1500}, "sclk": None},
            }}}}

    def profiles(self):
        return {"profiles": {"Gaming": {"type": "process",
                                        "filter": {"name": "vkcube"}}},
                "current_profile": None, "auto_switch": False,
                "profile_hooks": {}}

    def select_profile(self, name, auto):
        self.switched.append((name, auto))


def check_ui():
    app = QApplication.instance() or QApplication([])
    theme.set_mode("glass")
    app.setStyleSheet(theme.stylesheet())
    card = LactTuningCard()
    fake = FakeLact()
    card.client = fake
    card.reload()
    assert card.gpu_id == "gpu-1"
    assert card.apply_btn.isEnabled()
    assert card.fields["power_cap"].minimum() == 200.0
    assert card.fields["power_cap"].maximum() == 300.0
    assert card._collect() == fake.config, "Loading settings must not modify original config"
    assert not card.delete_btn.isEnabled(), "Default profile must not be deletable"
    assert card.live_readings["gpu"].text() == "167 MHz"
    assert card.live_readings["vram"].text() == "1258 MHz"
    assert card.live_readings["voltage"].text() == "552 mV"
    assert card.live_readings["temperature"].text() == "42.0 °C"
    assert card.live_readings["power"].text() == "55.0 W"
    assert card.live_readings["fan"].text() == "896 U/min"
    assert card.gpu_offset.isEnabled()
    assert card.gpu_offset.value() == 200
    assert card.fields["voltage_offset"].isEnabled()
    assert not card.fields["max_core_clock"].isEnabled()
    assert not card.advanced_group.isVisible()

    card.fields["power_cap"].setValue(275.0)
    changed = card._collect()
    assert changed["power_cap"] == 275.0
    assert changed["gpu_clock_offsets"] == {"0": 200}, "Unknown LACT fields must survive"
    assert changed["fan_control_settings"] == fake.config["fan_control_settings"]
    assert fake.config["power_cap"] == 250.0
    card.fields["power_cap"].setValue(250.0)
    card.gpu_offset.setValue(250)
    assert card._collect()["gpu_clock_offsets"] == {"0": 250}
    card.gpu_offset.setValue(200)
    # Enabling custom fans from a previously incomplete configuration must
    # ALWAYS provide the original daemon's required temperature key/interval.
    card.fan_enabled.setChecked(True)
    card.fan_curve.setPlainText("40: 30\n50: 35\n60: 50\n70: 75\n80: 100")
    fan_change = card._collect()
    assert fan_change["fan_control_enabled"] is True
    assert fan_change["fan_control_settings"]["temperature_key"] == "edge"
    assert fan_change["fan_control_settings"]["interval_ms"] == 500
    assert len(fan_change["fan_control_settings"]["curve"]) == 5
    card.fan_temperature.setCurrentIndex(card.fan_temperature.findData("junction"))
    assert card._collect()["fan_control_settings"]["temperature_key"] == "junction"
    card.fan_enabled.setChecked(False)
    card.advanced_toggle.click()
    assert card.advanced_group.isVisible() or not card.advanced_group.isHidden()
    card.advanced_toggle.click()

    card.profile_combo.setCurrentIndex(card.profile_combo.findData("Gaming"))
    assert card.delete_btn.isEnabled()
    assert card.rule_process.text() == "vkcube"
    card._load_profile()
    assert fake.switched[-1] == ("Gaming", False)

    card.extra.setPlainText("{invalid-json")
    try:
        card._collect()
    except ValueError:
        pass
    else:
        raise AssertionError("Malformed advanced config must be rejected")
    # Hardware names are still visible if the privileged engine is unavailable.
    from vitalux import sensors
    previous_gpu_info = sensors.gpu_info
    original_client = card.client
    class Offline:
        def devices(self):
            raise LactError("Vitalux GPU-Steuerung noch nicht eingerichtet.")
    try:
        sensors.gpu_info = lambda: [{"name": "AMD Radeon RX 9070 XT"}]
        card.client = Offline()
        card.reload()
        assert card.device_combo.itemText(0) == "AMD Radeon RX 9070 XT"
        assert not card.setup_button.isHidden()
        assert not card.apply_btn.isEnabled()
    finally:
        sensors.gpu_info = previous_gpu_info
        card.client = original_client
    card.close()
    card.deleteLater()
    app.processEvents()
    print("LACT Qt profile, config, fan and bounds checks: PASS")


if __name__ == "__main__":
    check_ui()
