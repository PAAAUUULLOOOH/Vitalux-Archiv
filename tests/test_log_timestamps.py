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
        (here / 'vitalux').mkdir()
        (here / 'vitalux' / '__init__.py').write_text(
            '__version__ = "0.9.3.70"\n', encoding='utf-8')
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
        assert all('[Vitalux v0.9.3.70]' in line for line in lines), lines
        assert any('malloc(): unaligned tcache chunk detected' in x for x in lines)
        assert any('exit code 134' in x for x in lines)
        assert any('automatische Wiederherstellung' in x for x in lines)
        errorlog = here/'state'/'vitalux'/'errors.log'
        assert errorlog.exists()
        assert re.search(r'\[Vitalux v0\.9\.3\.70\].*exit code 134', errorlog.read_text())


def test_installer_log():
    # The AppImage installer and first-run helper must have the same timestamp
    # and failing version format as the main application and restart watcher.
    with tempfile.TemporaryDirectory(prefix='vitalux-installer-logging-') as temporary:
        root = Path(temporary)
        (root/'packaging').mkdir()
        (root/'vitalux').mkdir()
        (root/'vitalux'/'__init__.py').write_text(
            '__version__ = "0.9.3.70"\n', encoding='utf-8')
        (root/'packaging'/'AppRun').write_bytes(
            (ROOT/'packaging'/'AppRun').read_bytes())
        helper = root/'packaging'/'appimage-integration.sh'
        helper.write_text('#!/bin/bash\necho "installation completed"\n', encoding='utf-8')
        env = os.environ.copy()
        env['APPDIR'] = str(root)
        env['XDG_STATE_HOME'] = str(root/'state')
        proc = subprocess.run(['bash', str(root/'packaging'/'AppRun'), '--install'],
                              env=env, capture_output=True, text=True, timeout=15)
        assert proc.returncode == 0, proc
        data = (root/'state'/'vitalux'/'installation.log').read_text().splitlines()
        assert any('installation completed' in line for line in data), data
        assert all(TIME.match(line) and '[Vitalux v0.9.3.70]' in line
                   for line in data), data


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
    test_installer_log()
    test_native_trace_start()
    print('Vitalux logs: all timestamps, version markers and native exit code 134: PASS')
