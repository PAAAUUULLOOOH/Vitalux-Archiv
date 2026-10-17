"""Regression: ZIP updater preserves one complete rollback snapshot."""
from pathlib import Path
import json
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vitalux import updater


def check_zip_restore():
    with tempfile.TemporaryDirectory(prefix="vitalux-zip-rollback-") as temp:
        root = Path(temp)
        (root/"vitalux").mkdir()
        (root/"vitalux"/"__main__.py").write_text("version='bad-current'\n")
        (root/"run.sh").write_text("new-launcher\n")
        (root/"assets").mkdir()
        (root/"assets"/"logo.txt").write_text("new")
        backup = root/".backup"
        (backup/"vitalux").mkdir(parents=True)
        (backup/"vitalux"/"__main__.py").write_text("version='stable-previous'\n")
        (backup/"root_files"/"assets").mkdir(parents=True)
        (backup/"root_files"/"run.sh").write_text("old-launcher\n")
        (backup/"root_files"/"assets"/"logo.txt").write_text("old")
        (backup/"metadata.json").write_text(json.dumps({
            "version":"0.9.3.51","root_files":["run.sh","assets"],
            "settings_saved":False}))
        assert updater.backup_available(str(root))
        updater.restore_previous(str(root), restore_settings=False)
        assert "stable-previous" in (root/"vitalux"/"__main__.py").read_text()
        assert (root/"run.sh").read_text() == "old-launcher\n"
        assert (root/"assets"/"logo.txt").read_text() == "old"
        assert updater.backup_available(str(root)), "A healthy restore must not automatically destroy recovery assets"
        assert not (root/".backup.old").exists()
        print("ZIP rollback restores application, launcher, and assets: PASS")


if __name__ == "__main__":
    check_zip_restore()
