"""Portable GPU setup regression checks: never require root or GPU access."""
import os
from pathlib import Path
import stat
import sys
import tempfile

sys.path.insert(0, os.getcwd())
from vitalux.gpu_setup import GPU_SETUP_FILES, stage_gpu_setup, remove_gpu_setup


def test_gpu_setup_staging():
    with tempfile.TemporaryDirectory(prefix="vitalux-gpu-test-") as original:
        source = Path(original)
        for path in GPU_SETUP_FILES:
            file = source / path
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes((path + "\n").encode() * 20)
        stage, installer = stage_gpu_setup(source)
        try:
            assert stage.parent.resolve() == Path(tempfile.gettempdir()).resolve()
            assert installer == stage / "packaging/vitalux-gpu-service.py"
            assert installer.is_file()
            assert stage != source
            assert stat.S_IMODE(stage.stat().st_mode) == 0o700
            for path in GPU_SETUP_FILES:
                item = stage / path
                assert item.read_bytes() == (source / path).read_bytes()
                assert not item.is_symlink()
                assert not item.stat().st_mode & stat.S_IWGRP
                assert not item.stat().st_mode & stat.S_IWOTH
        finally:
            remove_gpu_setup(stage)
        assert not stage.exists()
        remove_gpu_setup(stage)


def test_missing_source_is_atomic():
    with tempfile.TemporaryDirectory(prefix="vitalux-gpu-test-") as original:
        source = Path(original)
        (source / "packaging").mkdir()
        (source / "packaging/vitalux-gpu-service.py").write_text("print('test')")
        try:
            stage_gpu_setup(source)
        except FileNotFoundError:
            pass
        else:
            raise AssertionError("GPU setup must reject incomplete packages")


if __name__ == "__main__":
    test_gpu_setup_staging()
    test_missing_source_is_atomic()
    print("AppImage GPU staging, permissions and cleanup: PASS")
