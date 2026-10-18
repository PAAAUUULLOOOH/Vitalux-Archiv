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
        return {"power": {"cap_min": 200.0, "cap_max": 300.0,
                          "cap_current": 250.0},
                "fan": {"speed_max": 3000}}

    def device_clocks(self, _):
        return {"table": {"type": "amd", "value": {}}}

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

    card.fields["power_cap"].setValue(275.0)
    changed = card._collect()
    assert changed["power_cap"] == 275.0
    assert changed["gpu_clock_offsets"] == {"0": 200}, "Unknown LACT fields must survive"
    assert changed["fan_control_settings"] == fake.config["fan_control_settings"]
    assert fake.config["power_cap"] == 250.0
    card.fields["power_cap"].setValue(250.0)

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
    card.close()
    card.deleteLater()
    app.processEvents()
    print("LACT Qt profile, config, fan and bounds checks: PASS")


if __name__ == "__main__":
    check_ui()
