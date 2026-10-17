"""Vitalux four-part release version policy.

The last component runs from 1 to 99. After .99 the preceding component
increments, while the last component starts again at 1:
v0.9.3.99 -> v0.9.4.1 (never v0.9.3.100).
"""
import re
import sys

VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)\.(\d+)$")


def parse(version):
    match = VERSION_RE.fullmatch(str(version).strip())
    if not match:
        raise ValueError(f"Expected a four-part Vitalux version: {version!r}")
    major, minor, patch, build = map(int, match.groups())
    if not 1 <= build <= 99:
        raise ValueError(f"Vitalux suffix must be from 1 to 99: {version!r}")
    return major, minor, patch, build


def next_version(version):
    major, minor, patch, build = parse(version)
    if build == 99:
        return f"{major}.{minor}.{patch + 1}.1"
    return f"{major}.{minor}.{patch}.{build + 1}"


def verify_successor(previous, proposed):
    expected = next_version(previous)
    normalized = ".".join(map(str, parse(proposed)))
    if normalized != expected:
        raise ValueError(
            f"Version after v{previous.lstrip('v')} must be v{expected}, "
            f"not v{normalized}."
        )
    return normalized


if __name__ == "__main__":
    try:
        if len(sys.argv) == 3 and sys.argv[1] == "next":
            print(next_version(sys.argv[2]))
        elif len(sys.argv) == 4 and sys.argv[1] == "verify":
            print(f"Version transition valid: v{sys.argv[2].lstrip('v')} -> v"
                  f"{verify_successor(sys.argv[2], sys.argv[3])}")
        else:
            raise ValueError("Usage: versioning.py next VERSION | verify PREVIOUS PROPOSED")
    except ValueError as exc:
        raise SystemExit(str(exc))
