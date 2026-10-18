"""Deterministic performance lab tests, no GPU and no network required."""
import json
from pathlib import Path
import tempfile
from vitalux.insight_engine import MonitoringLab, telemetry, findings


def sample(cpu=55, gpu=88, vram=6, temp=65, clock=2450, gpu_name="RX 9070 XT"):
    return {
        "cpu": {"usage": cpu, "temp": 55},
        "ram": {"percent": 48},
        "gpus": [{"name": gpu_name, "usage": gpu, "temp": temp, "clock": clock,
                  "power": 190, "vram_used": vram, "vram_total": 16}],
    }


def test_detective_and_events():
    lab = MonitoringLab(max_samples=30)
    lab.ingest(sample(gpu=45), timestamp="2026-10-18T12:00:00+02:00")
    assert lab.detective()
    assert lab.events == lab.events
    lab.ingest(sample(gpu=99, vram=15, temp=98),
               limits={"gpu_temp": 90}, timestamp="2026-10-18T12:00:01+02:00")
    names = [e["title"] for e in lab.events]
    assert "GPU-Auslastung über 95 %" in names
    assert "Videospeicher über 90 %" in names
    assert "GPU-Temperatur überschreitet Warnwert" in names
    count = len(lab.events)
    lab.ingest(sample(gpu=99, vram=15, temp=99), limits={"gpu_temp":90})
    assert len(lab.events) == count, "No event spam while still above threshold"
    assert all("möglich" in text or "Warnwert" in text or "Messwerte" in text
               for _, text, _ in lab.detective({"gpu_temp":90}))
    lab.ingest(sample(gpu=None, vram=3, temp=None))
    assert any(e["title"] == "GPU-Sensor ausgefallen" for e in lab.events)
    for i in range(50):
        lab.ingest(sample(gpu=i))
    assert len(lab.history) == 30
    assert len(lab.recent) <= 20


def test_games_and_profiles():
    lab = MonitoringLab()
    lab.start_session("CS2")
    for x in range(5):
        lab.ingest(sample(gpu=x+40, clock=2400+x*20))
    result = lab.stop_session()
    assert result["name"] == "CS2" and result["samples"] == 5
    assert result["metrics"]["gpu_clock"]["min"] == 2400
    assert result["metrics"]["gpu_clock"]["max"] == 2480
    assert round(result["metrics"]["gpu_usage"]["avg"],1) == 42
    # Long sessions stay memory bounded without truncating averages.
    lab.start_session("Langzeit-Test")
    for i in range(1300):
        lab.ingest(sample(gpu=40 if i < 650 else 60))
    assert len(lab.session) <= 900
    long = lab.stop_session()
    assert long["samples"] == 1300
    assert long["metrics"]["gpu_usage"]["avg"] == 50
    try:
        lab.stop_session()
    except ValueError:
        pass
    else:
        raise AssertionError("Cannot stop twice")


def test_snapshots_persist_and_compare():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "insights-snapshots.json"
        lab = MonitoringLab(snapshot_path=p)
        lab.snapshot(0, sample(gpu=40))
        lab.snapshot(1, sample(gpu=70))
        result = dict((name, delta) for name,a,b,delta in lab.comparison())
        assert result["gpu_usage"] == 30
        assert json.loads(p.read_text())["snapshots"][0]["gpu"] == "RX 9070 XT"
        reopened = MonitoringLab(snapshot_path=p)
        assert reopened.comparison() == lab.comparison()
        reopened.snapshot(1, sample(gpu=70, gpu_name="Other GPU"))
        assert reopened.comparison() == [], "Do not compare different GPU devices"
        p.write_text("{invalid", encoding="utf-8")
        assert MonitoringLab(snapshot_path=p).snapshots == [None, None]


def test_mangohud_fps_source():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "mangohud.csv"
        path.write_text("engine,runtime\nGPU,RDNA4\nfps,frametime,gpu_load\n"
                        + "\n".join(f"{fps},{1000/fps:.3f},70"
                                    for fps in [120]*99 + [42]) + "\n", encoding="utf-8")
        lab = MonitoringLab()
        summary = lab.import_mangohud(path)
        assert summary["samples"] == 100
        assert 118 < summary["avg_fps"] < 120
        assert summary["one_percent_low_approx"] == 42.0
        assert summary["p99_frametime_ms"] > 8
        lab.start_session("test")
        lab.ingest(sample())
        lab.stop_session()
        lab.import_mangohud(path)
        out = Path(tmp) / "session.json"
        lab.export_session(out)
        assert json.loads(out.read_text())["mangohud"]["source"] == "mangohud.csv"
        bad = Path(tmp) / "empty.csv"
        bad.write_text("hello,world\n", encoding="utf-8")
        try:
            lab.import_mangohud(bad)
        except ValueError:
            pass
        else:
            raise AssertionError("Reject unknown log format")


if __name__ == "__main__":
    test_detective_and_events()
    test_games_and_profiles()
    test_snapshots_persist_and_compare()
    test_mangohud_fps_source()
    print("Detective, gaming, comparisons, timeline and MangoHud: PASS")
