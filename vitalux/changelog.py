"""Read the local, shipped Vitalux changelog without network access."""
from pathlib import Path
import re

CHANGELOG_PATH = Path(__file__).resolve().parent.parent / "CHANGELOG.md"
_HEADING = re.compile(r"^## \[v(\d+\.\d+\.\d+(?:\.\d+)?)\](?:\s+-.*)?$", re.M)


def entries(path=None):
    """Newest-first (version, changes) pairs. Unknown files fail quietly."""
    source = Path(path) if path is not None else CHANGELOG_PATH
    try:
        data = source.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return []
    heads = list(_HEADING.finditer(data))
    results = []
    for idx, match in enumerate(heads):
        until = heads[idx + 1].start() if idx + 1 < len(heads) else len(data)
        body = data[match.end():until]
        changes = [line.strip()[2:].strip() for line in body.splitlines()
                   if line.strip().startswith("- ") and len(line.strip()) > 2]
        if changes:
            results.append((match.group(1), changes))
    return results


def version_notes(version, path=None):
    for ident, changes in entries(path):
        if ident == str(version).lstrip("v"):
            return changes
    return []


def displayed_changes(changes):
    return "\n".join("• " + change for change in changes)
