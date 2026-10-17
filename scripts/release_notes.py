"""Generate precise release notes from the same changelog shipped in Vitalux.

Fails the publication if the version lacks a changelog entry.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from vitalux.changelog import version_notes


def build(version, path=ROOT / "CHANGELOG.md"):
    ver = str(version).lstrip("v")
    german = version_notes(ver, path, lang="de")
    english = version_notes(ver, ROOT / "CHANGELOG.en.md", lang="en")
    if not german:
        raise ValueError(f"CHANGELOG.md: missing German changes for v{ver}")
    if not english:
        raise ValueError(f"CHANGELOG.en.md: missing English changes for v{ver}")
    return (f"## Deutsch\n\n### Neu in Vitalux v{ver}\n\n"
            + "\n".join("- " + item for item in german)
            + "\n\n## English\n\n"
            + f"### What's new in Vitalux v{ver}\n\n"
            + "\n".join("- " + item for item in english)
            + "\n\n[Changelog (Deutsch)]"
              "(https://github.com/PAAAUUULLOOOH/Vitalux/blob/main/CHANGELOG.md)"
              " · [Changelog (English)]"
              "(https://github.com/PAAAUUULLOOOH/Vitalux/blob/main/CHANGELOG.en.md)\n")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: release_notes.py VERSION OUTPUT_FILE")
    try:
        notes = build(sys.argv[1])
    except ValueError as exc:
        raise SystemExit(str(exc))
    dest = Path(sys.argv[2])
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(notes, encoding="utf-8")
    print(f"Vitalux v{sys.argv[1].lstrip('v')}: validated changelog and release notes")
