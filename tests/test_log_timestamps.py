"""A native SIGABRT is timestamped without relying on the Python exception hook.

The fake bundled interpreter simulates normal QT log output and a glibc abort.
This uses no real GUI or system Qt runtime and does not alter user files.
"""
from datetime import datetime
from pathlib import Path
import os
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TIME = re.compile(r'^\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}\] ')


def test_launcher():
    with tempfile.TemporaryDirectory(prefix='vitalux-stamped-crash-') as temporary:
        here = Path(temporary)
        (here / 'runtime' / 'bin').mkdir(parents=True)
        (here / 'run.sh').write_bytes((ROOT/'run.sh').read_bytes())
        fake = here / 'runtime' / 'bin' / 'python3.12'
        fake.write_text(
            '#!/usr/bin/env bash\n'
            'if [[ "${1:-}" == "-c" ]]; then exit 0; fi\n'
            'if [[ "${1:-}" == "-m" ]]; then\n'
            '  echo "qt.qpa.services: test portal diagnostic" >&2\n'
            '  echo "malloc(): unaligned tcache chunk detected" >&2\n'
            '  exit 134\n'
            'fi\n'
            'exit 0\n', encoding='utf-8')
        fake.chmod(0o755)
        env = os.environ.copy()
        env['XDG_STATE_HOME'] = str(here/'state')
        env['VITALUX_GUARDED'] = '1'
        env.pop('APPIMAGE', None)
        env.pop('DISPLAY', None)
        env.pop('WAYLAND_DISPLAY', None)
        result = subprocess.run(['bash', str(here / 'run.sh')], env=env,
                                capture_output=True, text=True, timeout=15)
        assert result.returncode == 134, result
        logfile = here/'state'/'vitalux'/'vitalux.log'
        lines = [line for line in logfile.read_text().splitlines() if line]
        assert len(lines) >= 5, lines
        assert all(TIME.match(line) for line in lines), lines
        assert any('malloc(): unaligned tcache chunk detected' in x for x in lines)
        assert any('exit code 134' in x for x in lines)
        assert any('automatische Wiederherstellung' in x for x in lines)


def test_native_trace_start():
    with tempfile.TemporaryDirectory(prefix='vitalux-stamped-errors-') as temporary:
        code = (
            'import os\n'
            'from vitalux import diagnostics\n'
            'diagnostics.enable_native_crash_trace()\n'
            'assert diagnostics.LOG_PATH.exists()\n'
        )
        env = os.environ.copy()
        env['XDG_STATE_HOME'] = temporary
        subprocess.run([sys.executable, '-c', code], cwd=ROOT,
                       env=env, check=True, timeout=10)
        data = (Path(temporary)/'vitalux'/'errors.log').read_text()
        assert re.search(
            r'=== Vitalux .* started '
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+[+-]\d{2}:\d{2}',
            data), data


if __name__ == '__main__':
    test_launcher()
    test_native_trace_start()
    print('Crash logger: each native stderr line, exit 134 and errors.log start have timestamps: PASS')
