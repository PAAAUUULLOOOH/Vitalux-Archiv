"""Release-number boundary regressions for the four-component Vitalux scheme."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import versioning


def check():
    assert versioning.parse("v0.9.3.70") == (0, 9, 3, 70)
    assert versioning.next_version("0.9.3.70") == "0.9.3.71"
    assert versioning.next_version("v0.9.3.98") == "0.9.3.99"
    assert versioning.next_version("v0.9.3.99") == "0.9.4.1"
    assert versioning.next_version("v0.9.4.1") == "0.9.4.2"
    assert versioning.next_version("v0.9.9.99") == "0.9.10.1"
    assert versioning.verify_successor("v0.9.3.99", "0.9.4.1") == "0.9.4.1"
    for previous, proposed in [
        ("0.9.3.99", "0.9.3.100"),
        ("0.9.3.99", "0.9.4.2"),
        ("0.9.3.98", "0.9.4.1"),
        ("0.9.3.70", "0.9.3.72"),
    ]:
        try:
            versioning.verify_successor(previous, proposed)
            raise AssertionError((previous, proposed))
        except ValueError:
            pass
    for invalid in ("0.9.3.0", "0.9.3.100", "0.9.3", "bad"):
        try:
            versioning.parse(invalid)
            raise AssertionError(invalid)
        except ValueError:
            pass
    script = ROOT / "scripts" / "versioning.py"
    ok = subprocess.run([sys.executable, str(script), "verify",
                         "v0.9.3.99", "0.9.4.1"], capture_output=True, text=True)
    assert ok.returncode == 0, ok.stderr
    bad = subprocess.run([sys.executable, str(script), "verify",
                          "v0.9.3.99", "0.9.3.100"], capture_output=True, text=True)
    assert bad.returncode != 0
    print("Release versioning: .98 -> .99 -> next patch .1; invalid .100 blocked: PASS")


if __name__ == "__main__":
    check()
