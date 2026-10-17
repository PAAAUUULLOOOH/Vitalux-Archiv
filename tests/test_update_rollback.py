"""Test real shell dispatch and automatic one-version AppImage rollback."""
import os
from pathlib import Path
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
APP_RUN = ROOT / "packaging" / "AppRun"
GUARD = ROOT / "packaging" / "appimage-rollback-watch.sh"


def setup(temp, code, backup=True):
    temp = Path(temp)
    appdir = temp / "mounted"
    (appdir / "packaging").mkdir(parents=True, exist_ok=True)
    (appdir / "run.sh").write_text(
        "#!/bin/bash\n"
        f"exit {code}\n", encoding="utf-8")
    (appdir / "run.sh").chmod(0o755)
    target = temp / "Vitalux.AppImage"
    target.write_text("#!/bin/sh\nexit 4\n", encoding="utf-8")
    target.chmod(0o755)
    old = target.with_name(target.name + ".previous")
    marker = temp / "old-started"
    if backup:
        old.write_text(
            "#!/bin/sh\n"
            'printf "recovered" > "$TEST_RECOVERY_MARKER"\n'
            "exit 0\n", encoding="utf-8")
        old.chmod(0o755)
    env = os.environ.copy()
    env.update(HOME=str(temp), APPDIR=str(appdir), APPIMAGE=str(target),
               TEST_RECOVERY_MARKER=str(marker), XDG_STATE_HOME=str(temp/"state"))
    (appdir / "packaging" / GUARD.name).write_bytes(GUARD.read_bytes())
    return appdir, target, old, marker, env


def launch(env):
    return subprocess.run(["bash", str(APP_RUN), "--launch"], env=env,
                          capture_output=True, text=True, timeout=12)


def assert_success_keeps_last_previous():
    with tempfile.TemporaryDirectory(prefix="vitalux-safe-exit-") as td:
        _, target, backup, marker, env = setup(td, 0)
        result = launch(env)
        assert result.returncode == 0, result.stderr
        assert backup.exists(), "Normal application exit wrongly deleted fallback"
        assert target.read_text().endswith("exit 4\n")
        assert not marker.exists(), "Rollback on normal exit"


def assert_abnormal_crash_restores_previous():
    with tempfile.TemporaryDirectory(prefix="vitalux-bad-exit-") as td:
        _, target, backup, marker, env = setup(td, 42)
        result = launch(env)
        assert result.returncode == 0, result.stderr
        for _ in range(30):
            if marker.exists():
                break
            time.sleep(.05)
        assert marker.exists(), "Recovered app was not automatically relaunched"
        assert marker.read_text() == "recovered"
        assert not backup.exists(), "Crash rollback must consume the old .previous"
        assert "recovered" in target.read_text(), "Previous version not restored"
        log = Path(td)/"state"/"vitalux"/"restart.log"
        assert "Recovered previous Vitalux version" in log.read_text()


def assert_shutdown_never_rolls_back():
    with tempfile.TemporaryDirectory(prefix="vitalux-normal-signal-") as td:
        _, target, backup, marker, env = setup(td, 143)
        result = launch(env)
        assert result.returncode == 143
        assert backup.exists(), "Normal shutdown destroyed the backup"
        assert target.read_text().endswith("exit 4\n")
        assert not marker.exists()


def assert_no_backup_unchanged():
    with tempfile.TemporaryDirectory(prefix="vitalux-no-backup-") as td:
        _, target, backup, marker, env = setup(td, 0, backup=False)
        result = launch(env)
        assert result.returncode == 0
        assert not backup.exists()
        assert not marker.exists()


if __name__ == "__main__":
    assert_success_keeps_last_previous()
    assert_abnormal_crash_restores_previous()
    assert_shutdown_never_rolls_back()
    assert_no_backup_unchanged()
    print("AppImage rollback: normal exit, crash recovery, shutdown and fresh launch PASS")
