"""Regression checks for the native Vitalux / LACT interface."""
import json
import os
import socket
import tempfile
import threading

from vitalux.lact_client import (
    LactClient, LactError, format_fan_curve, merged_gpu_config, parse_fan_curve
)


def test_merge_preserves_unknown_fields():
    original = {"power_cap": 250.0, "gpu_clock_offsets": {"0": -100},
                "pmfw_options": {"zero_rpm": True}}
    merged = merged_gpu_config(original, {"power_cap": 275.0})
    assert merged["power_cap"] == 275.0
    assert merged["gpu_clock_offsets"] == {"0": -100}
    assert merged["pmfw_options"]["zero_rpm"]
    assert original["power_cap"] == 250.0


def test_reject_invalid_power_and_fields():
    for amount in (float("nan"), float("inf"), -1, 0, True):
        try:
            merged_gpu_config({}, {"power_cap": amount})
        except ValueError:
            pass
        else:
            raise AssertionError(f"Invalid cap accepted: {amount!r}")
    try:
        merged_gpu_config({}, {"unwanted": "field"})
    except ValueError:
        pass
    else:
        raise AssertionError("Unknown field accepted")


def test_fan_curve():
    curve = parse_fan_curve("40: 30\n50: 35\n60: 50\n70: 75\n80: 100")
    assert curve["60"] == .5
    assert parse_fan_curve(format_fan_curve(curve)) == curve
    for invalid in ("40: 20", "40: 80\n50: 20",
                    "40: 10\n40: 40", "40: NaN\n50: 90"):
        try:
            parse_fan_curve(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Invalid curve accepted: {invalid!r}")


def test_unix_transport_and_daemon_error():
    with tempfile.TemporaryDirectory() as tmp:
        sockpath = os.path.join(tmp, "lactd.sock")
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(sockpath)
        server.listen(1)
        received = []

        def worker():
            conn, _ = server.accept()
            with conn:
                message = b""
                while not message.endswith(b"\n"):
                    message += conn.recv(4096)
                received.append(json.loads(message))
                conn.sendall(b'{"status":"ok","data":[{"id":"gpu-1","name":"Test"}]}\n')
            server.close()

        thread = threading.Thread(target=worker)
        thread.start()
        assert LactClient(sockpath).devices() == [{"id": "gpu-1", "name": "Test"}]
        thread.join(timeout=2)
        assert received == [{"command": "list_devices"}]
        assert not thread.is_alive()


if __name__ == "__main__":
    test_merge_preserves_unknown_fields()
    test_reject_invalid_power_and_fields()
    test_fan_curve()
    test_unix_transport_and_daemon_error()
    print("LACT client regressions: PASS")
