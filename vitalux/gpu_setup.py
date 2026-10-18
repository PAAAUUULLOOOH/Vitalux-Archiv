"""Safe, temporary hand-off of bundled GPU setup files to a polkit process.

AppImage files can live on a user-mounted FUSE filesystem inaccessible to a
privileged process. Stage only the required files in a normal, private /tmp
directory before invoking pkexec. The caller must remove the staging folder
after the process exits.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import tempfile


GPU_SETUP_FILES = (
    "packaging/vitalux-gpu-service.py",
    "bin/vitalux-gpu-engine",
    "LICENSES/LACT-MIT.txt",
)


def stage_gpu_setup(package_root):
    package_root = Path(package_root)
    for relative in GPU_SETUP_FILES:
        if not (package_root / relative).is_file():
            raise FileNotFoundError(f"Required Vitalux GPU file missing: {relative}")
    stage = Path(tempfile.mkdtemp(prefix="vitalux-gpu-"))
    try:
        for relative in GPU_SETUP_FILES:
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(package_root / relative, target)
            target.chmod(0o500 if relative.startswith("bin/") else 0o400)
        return stage, stage / "packaging/vitalux-gpu-service.py"
    except BaseException:
        remove_gpu_setup(stage)
        raise


def remove_gpu_setup(stage):
    if stage is not None:
        shutil.rmtree(stage, ignore_errors=True)
