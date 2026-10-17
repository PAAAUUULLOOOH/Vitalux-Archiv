"""User-readable local crash log / opt-in diagnostic report.

Reports are written locally; the application never uploads them.
"""
import json
import faulthandler
import os
import platform
import sys
import traceback
from datetime import datetime
from pathlib import Path

from . import __version__

LOG_PATH = (Path(os.environ.get('XDG_STATE_HOME') or Path.home()/'.local'/'state') /
            'vitalux' / 'errors.log')


_fatal_log = None


def enable_native_crash_trace():
    """Capture fatal Qt/native stack traces when the GUI crashes."""
    global _fatal_log
    if _fatal_log is not None:
        return
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        _fatal_log = LOG_PATH.open('a', encoding='utf-8')
        _fatal_log.write(
            f'\n=== Vitalux {__version__} started '
            f'{datetime.now().astimezone().isoformat()} '
            f'(PID {os.getpid()}) ===\n'
        )
        # Flush before handing the descriptor to the native crash handler:
        # a SIGABRT may never return to Python to flush buffered text.
        _fatal_log.flush()
        faulthandler.enable(file=_fatal_log, all_threads=True)
    except (OSError, RuntimeError, ValueError):
        _fatal_log = None


def log_exception(kind, value, tb=None):
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open('a', encoding='utf-8') as log:
            # Always include date, timezone and failing version on *every*
            # Python exception line. Native faulthandler frames are surrounded
            # by the timestamped startup marker and the shell's crash footer.
            at = datetime.now().astimezone().isoformat()
            log.write(f'[{at}] [Vitalux v{__version__}] Python exception\n')
            for line in ''.join(traceback.format_exception(kind, value, tb)).splitlines():
                log.write(f'[{at}] [Vitalux v{__version__}] {line}\n')
            log.flush()
    except OSError:
        pass


def exception_hook(kind, value, tb):
    log_exception(kind, value, tb)
    sys.__excepthook__(kind, value, tb)


def export_report(path, include_errors=False, sample=None):
    """Explicit export; may contain hardware / personal host information."""
    report = {'vitalux_version': __version__, 'created_at': datetime.now().astimezone().isoformat(),
              'python': platform.python_version(), 'platform': platform.platform(),
              'errors_log_path': str(LOG_PATH), 'last_sample': sample}
    if include_errors and LOG_PATH.exists():
        report['recent_errors'] = LOG_PATH.read_text(encoding='utf-8', errors='replace')[-16000:]
    with open(path, 'w', encoding='utf-8') as out:
        json.dump(report, out, indent=2, ensure_ascii=False, default=str)
