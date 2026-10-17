"""Non-destructive offline diagnosis of a Vitalux portable extraction.

Python/Qt test and ELF library inspection only. Optional --display validates the
actual active Wayland/X11 Qt plugin; no disks are benchmarked or changed.
"""
from __future__ import annotations
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
QT = ROOT / 'runtime/lib/python3.12/site-packages/PySide6/Qt'
LIB = QT / 'plugins/platforms'
REQUIRED_GLIBC = (2, 38)

def _run(command, timeout=8, env=None):
    try:
        return subprocess.run(command, capture_output=True, text=True,
                              timeout=timeout, env=env, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None

def check_arch():
    architecture = platform.machine().lower()
    libc, version = platform.libc_ver()
    print(f'Architektur: {architecture}; libc: {libc} {version or "unbekannt"}')
    if architecture not in ('x86_64', 'amd64'):
        print('FEHLER: Dieses Paket ist nur fuer Linux x86-64 gebaut.')
        return False
    m = re.match(r'(\d+)\.(\d+)', version)
    if libc != 'glibc' or not m:
        print('HINWEIS: glibc konnte nicht ermittelt werden. musl wird nicht unterstuetzt.')
        return False
    if tuple(map(int, m.groups())) < REQUIRED_GLIBC:
        print('FEHLER: gebuendelte fio-Engine benoetigt glibc 2.38 oder neuer.')
        return False
    return True

def check_linker():
    targets = {
        'Python': ROOT / 'runtime/bin/python3.12',
        'Benchmark': ROOT / 'bin/fio.real',
        'Wayland': LIB / 'libqwayland.so',
        'X11/xcb': LIB / 'libqxcb.so',
        'Offscreen': LIB / 'libqoffscreen.so',
    }
    env = os.environ.copy()
    # Mirrors the actual launcher and fio wrapper.
    env['LD_LIBRARY_PATH'] = ':'.join(str(p) for p in (ROOT / 'lib', ROOT / 'tools-lib')
                                     if p.is_dir()) + (':' + env['LD_LIBRARY_PATH']
                                                       if env.get('LD_LIBRARY_PATH') else '')
    good = True
    if not shutil.which('ldd'):
        print('HINWEIS: ldd nicht vorhanden. ELF-Bibliotheken konnten nicht inspiziert werden.')
        return True
    for name, path in targets.items():
        if not path.is_file():
            print(f'FEHLER: {name}: Datei fehlt ({path.relative_to(ROOT)})')
            good = False
            continue
        response = _run(['ldd', str(path)], timeout=8, env=env)
        if response is None:
            print(f'HINWEIS: {name}: ldd konnte nicht ausgefuehrt werden.')
            continue
        missing = sorted(set(re.findall(r'^\s*(\S+)\s+=>\s+not found\s*$',
                                        response.stdout + '\n' + response.stderr,
                                        flags=re.MULTILINE)))
        if missing:
            good = False
            print(f'FEHLER: {name}: nicht aufloesbare Bibliotheken: {", ".join(missing)}')
        elif response.returncode != 0:
            good = False
            print(f'FEHLER: {name}: ldd fehlgeschlagen: '
                  f'{(response.stderr or response.stdout).strip()[:250]}')
        else:
            print(f'OK: {name}: ELF-Abhaengigkeiten aufgeloest')
    return good

def check_gui(native=False):
    env = os.environ.copy()
    env['QT_QPA_PLATFORM'] = 'offscreen'
    command = [sys.executable, '-c',
               'from PySide6.QtWidgets import QApplication; import psutil; '
               'from PySide6.QtSvg import QSvgRenderer; '
               'a=QApplication([]); print("Qt:",a.platformName(),"psutil:",psutil.__version__)']
    response = _run(command, timeout=12, env=env)
    if response is None or response.returncode:
        print('FEHLER: Python/Qt konnte nicht geladen werden:',
              (response.stderr[-600:] if response else 'Zeitlimit/Programm nicht gefunden'))
        return False
    print('OK: Python / Qt / psutil:', response.stdout.strip())
    if native:
        platform_name = ('wayland' if os.environ.get('WAYLAND_DISPLAY')
                         else 'xcb' if os.environ.get('DISPLAY') else None)
        if platform_name is None:
            print('HINWEIS: Keine grafische Sitzung erkannt. Kein Wayland/X11-Test moeglich.')
            return True
        env['QT_QPA_PLATFORM'] = platform_name
        response = _run(command, timeout=12, env=env)
        if response is None or response.returncode:
            print(f'FEHLER: native Qt-Sitzung ({platform_name}) konnte nicht geoeffnet werden:',
                  (response.stderr[-600:] if response else 'Zeitlimit'))
            return False
        print(f'OK: Qt {platform_name} / KDE-Sitzung: {response.stdout.strip()}')
    return True

def check_fio():
    path = ROOT / 'bin/fio'
    if not path.is_file():
        print('FEHLER: gebuendelte fio-Engine fehlt.')
        return False
    result = _run([str(path), '--version'])
    if result is None or result.returncode:
        print('FEHLER: fio kann nicht gestartet werden:',
              (result.stderr[-350:] if result else 'Zeitlimit'))
        return False
    print('OK: fio:', result.stdout.strip())
    eng = _run([str(path), '--enghelp'])
    if eng is None or eng.returncode != 0 or 'libaio' not in eng.stdout:
        print('FEHLER: fio/libaio ist nicht verfuegbar.')
        return False
    print('OK: fio/libaio verfuegbar (ohne Benchmark-Schreibzugriff)')
    return True

def main():
    native = '--display' in sys.argv[1:]
    print('Vitalux Portable-Kompatibilitaetspruefung (keine Installation)')
    result = [check_arch(), check_linker(), check_gui(native), check_fio()]
    print('S.M.A.R.T.: UDisks2-Systemdienst wird genutzt, sofern vorhanden;')
    print('          smartctl ist nicht gebuendelt; Zugriffsrechte bleiben vom System abhaengig.')
    print('Ergebnis:', 'OK' if all(result) else 'EINSCHRAENKUNGEN GEFUNDEN')
    return 0 if all(result) else 1

if __name__ == '__main__':
    sys.exit(main())
