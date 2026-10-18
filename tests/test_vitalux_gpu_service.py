"""Regression tests for the opt-in, polkit-approved Vitalux GPU system service.

Never run system installation or privileged commands in these tests.
"""
from __future__ import annotations
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
installer = ROOT / "packaging" / "vitalux-gpu-service.py"
spec = importlib.util.spec_from_file_location("vitalux_gpu_service", installer)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_safe_permission_injection():
    out = module.configured_for_user("", "paul")
    assert out == "daemon:\n  admin_user: paul\n"
    out = module.configured_for_user("gpus: {}\n", "paul")
    assert out.endswith("daemon:\n  admin_user: paul\n")
    out = module.configured_for_user("daemon:\n  log_level: info\ngpus: {}\n", "paul")
    assert "daemon:\n  admin_user: paul\n  log_level: info\n" in out
    assert "gpus: {}" in out
    assert module.configured_for_user(out, "paul") == out
    try:
        module.configured_for_user("daemon:\n  admin_user: other\n", "paul")
    except RuntimeError:
        pass
    else:
        raise AssertionError("Must not overwrite another administrator")
    try:
        module.configured_for_user("daemon: {admin_user: other}\n", "paul")
    except RuntimeError:
        pass
    else:
        raise AssertionError("Must not overwrite unsupported configuration")


def test_fixed_opaque_backend_and_unit():
    assert module.ENGINE.name == "vitalux-gpu-engine"
    assert str(module.UNIT).endswith("/vitalux-gpu.service")
    assert module.SERVICE.count("ExecStart=/usr/local/libexec/vitalux/gpu-engine daemon") == 1
    assert "lactd.service" not in module.SERVICE
    assert "WantedBy=multi-user.target" in module.SERVICE
    assert (ROOT / "LICENSES" / "LACT-MIT.txt").is_file()


if __name__ == "__main__":
    test_safe_permission_injection()
    test_fixed_opaque_backend_and_unit()
    print("Vitalux GPU service setup checks: PASS")
