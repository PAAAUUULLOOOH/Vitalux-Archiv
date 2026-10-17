#!/usr/bin/env python3
"""Build distributable Vitalux ZIPs while keeping execute bits and checksum changes."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib
import os
import sys

def files(root):
    for p in sorted(root.rglob("*")):
        if p.is_file() and not any(x in {"__pycache__", ".git", ".pytest_cache"} for x in p.relative_to(root).parts) and not p.name.endswith((".pyc", ".pyo")):
            yield p

def sha(p):
    with p.open("rb") as f:
        h = hashlib.sha256()
        for block in iter(lambda: f.read(1024*1024), b""):
            h.update(block)
        return h.digest()

def put(z, p, root):
    # Prefix is the published folder name. ZipFile.write preserves Unix permission bits.
    z.write(p, arcname=(root.name + "/" + p.relative_to(root).as_posix()))

def main():
    if len(sys.argv) != 5:
        raise SystemExit("Usage: create-release-archives.py NEW_DIR BASELINE_DIR OUT_DIR PREVIOUS_VERSION")
    current, previous, out = map(lambda s: Path(s).resolve(), sys.argv[1:4])
    previous_version = sys.argv[4]
    out.mkdir(parents=True, exist_ok=True)
    ver = current.name.removeprefix("Vitalux-v")
    full = out / f"Vitalux-v{ver}-linux-x86_64.zip"
    changed = out / f"Vitalux-v{ver}-Update-von-v{previous_version}.zip"

    with ZipFile(full, "w", ZIP_DEFLATED, compresslevel=6, allowZip64=True) as z:
        for p in files(current):
            put(z, p, current)
    print(f"Created {full.name} ({full.stat().st_size:,} bytes)")

    # Portable delta is for manual overlays only. Built-in updater uses full archives.
    differences = []
    current_paths = set()
    for p in files(current):
        rel = p.relative_to(current)
        current_paths.add(rel)
        old = previous / rel
        if not old.is_file() or p.stat().st_size != old.stat().st_size or sha(p) != sha(old):
            differences.append(p)
    removed = sorted(str(p.relative_to(previous)) for p in files(previous)
                     if p.relative_to(previous) not in current_paths)
    with ZipFile(changed, "w", ZIP_DEFLATED, compresslevel=6, allowZip64=True) as z:
        for p in differences:
            put(z, p, current)
        z.writestr("README-UPDATE.txt",
                   "Vitalux-Update fuer die ZIP-Version. Dateien nur in eine bestehende "
                   "entpackte Vitalux-Installation der Vorversion uebernehmen; "
                   "vorher sichern. Entfernte Dateien stehen in ENTFERNTE-DATEIEN.txt. "
                   "NICHT auf AppImages anwenden; diese werden ueber GitHub aktualisiert.\n")
        z.writestr("ENTFERNTE-DATEIEN.txt", "\n".join(removed) + "\n")
    print(f"Created {changed.name} ({len(differences)} changed, {len(removed)} removed)")

if __name__ == "__main__":
    main()
