"""Bundle narrowly scoped Qt Quick widgets, QML imports and shared libs.

The Vitalux portable runtime deliberately ships only required PySide6
modules, not the whole PySide6 Essentials wheel. Pull from the exact same
PySide6 version as the runtime, preserving its other compiled bindings.
"""
from pathlib import Path, PurePosixPath
import shutil
import sys
import zipfile


BINDINGS = {
    'QtQuick.abi3.so', 'QtQuickWidgets.abi3.so',
    'QtQml.abi3.so', 'QtNetwork.abi3.so', 'QtOpenGL.abi3.so',
}
LIBRARIES = {
    'libQt6Quick.so.6',
    'libQt6QuickWidgets.so.6',
    'libQt6Qml.so.6',
    'libQt6QmlModels.so.6',
    'libQt6QmlWorkerScript.so.6',
    'libQt6QmlMeta.so.6',
    'libQt6QmlCompiler.so.6',
    'libQt6QmlCore.so.6',
}
# Only the plain QtQuick Image/Item QML imports are used; never bundle
# the substantially larger Qt Quick Controls, 3D, or multimedia modules.
IMPORT_MODULES = {'QtQuick', 'QtQml'}


def include(path):
    parts = path.parts
    if len(parts) < 2 or parts[0] != 'PySide6':
        return False
    if len(parts) == 2 and parts[1] in BINDINGS:
        return True
    if len(parts) == 2 and parts[1].startswith('libpyside6'):
        return any(part in parts[1].lower() for part in ('qml', 'quick'))
    if len(parts) == 4 and parts[1:3] == ('Qt', 'lib'):
        return parts[-1] in LIBRARIES
    if len(parts) >= 4 and parts[1:3] == ('Qt', 'qml'):
        module = parts[3]
        if module not in IMPORT_MODULES:
            return False
        if module == 'QtQuick':
            return len(parts) == 5  # root plugin only
        # QtQml root, plus Models/WorkerScript direct modules if needed.
        return len(parts) == 5 or (len(parts) == 6 and parts[4] in ('Models', 'WorkerScript'))
    return False


def main():
    if len(sys.argv) != 3:
        sys.exit('Usage: bundle-quick-runtime.py PySide6_Essentials.whl STAGED_ROOT')
    wheel, staged = Path(sys.argv[1]), Path(sys.argv[2])
    site = staged / 'runtime/lib/python3.12/site-packages'
    if not site.is_dir():
        raise SystemExit(f'No packaged Python site: {site}')
    copied = set()
    with zipfile.ZipFile(wheel) as archive:
        for member in archive.infolist():
            name = PurePosixPath(member.filename)
            if not include(name) or member.is_dir():
                continue
            target = site.joinpath(*name.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open('wb') as dest:
                shutil.copyfileobj(source, dest)
            copied.add(name.name)
            print('Qt Quick runtime:', target.relative_to(staged))
    needed = {
        'QtQuick.abi3.so', 'QtQuickWidgets.abi3.so',
        'libQt6Quick.so.6', 'libQt6QuickWidgets.so.6',
        'libQt6Qml.so.6', 'qmldir',
    }
    missing = needed - copied
    if missing:
        raise SystemExit(f'Missing Qt Quick wheel components: {sorted(missing)}')
    print(f'Bundled {len(copied)} unique Qt Quick/QML runtime filenames')


if __name__ == '__main__':
    main()
