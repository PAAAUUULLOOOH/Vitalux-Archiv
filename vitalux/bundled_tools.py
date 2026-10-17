"""Resolve explicit packaged tools before searching the host PATH.

Portable builds place tools in bin/ (fio, smartctl) with their shared
libraries in lib/.  Older layouts (vendor/bin, runtime/bin) still work.
"""
from __future__ import annotations
import os
import shutil
from pathlib import Path

SUPPORTED = {'smartctl', 'fio'}


def find_tool(name, *, root=None):
    if name not in SUPPORTED:
        raise ValueError('Unsupported external helper')
    basedir = Path(root) if root else Path(__file__).resolve().parent.parent
    for subfolder in ('bin', 'vendor/bin', 'runtime/bin'):
        candidate = basedir / subfolder / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return shutil.which(name)
