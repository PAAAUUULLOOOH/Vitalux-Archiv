"""Bundle only the Qt OpenGL widget pieces from an exact-version wheel.

Keep the existing PySide6-Essentials runtime intact. In particular, do not
replace PySide6/__init__.py or any of its other C++ extensions.
"""
import pathlib
import sys
import zipfile


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: bundle-opengl-runtime.py PySide6_Addons.whl STAGED_ROOT")
    wheel = pathlib.Path(sys.argv[1])
    root = pathlib.Path(sys.argv[2])
    site = root / 'runtime/lib/python3.12/site-packages'
    if not site.is_dir():
        raise SystemExit(f"Missing Vitalux site-packages: {site}")
    names = {
        'QtOpenGLWidgets.abi3.so',
        'QtOpenGL.abi3.so',
        'libQt6OpenGLWidgets.so.6',
        'libQt6OpenGL.so.6',
    }
    copied = set()
    with zipfile.ZipFile(wheel) as archive:
        for info in archive.infolist():
            src = pathlib.PurePosixPath(info.filename)
            if not info.filename.startswith('PySide6/') or src.name not in names:
                continue
            if src.parts[1:3] not in [('Qt', 'lib')]:
                if len(src.parts) != 2:
                    continue
            output = site.joinpath(*src.parts)
            output.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as stream, output.open('wb') as target:
                import shutil
                shutil.copyfileobj(stream, target)
            copied.add(src.name)
            print(f'Bundled: {output.relative_to(root)}')
    required = {'QtOpenGLWidgets.abi3.so', 'libQt6OpenGLWidgets.so.6', 'libQt6OpenGL.so.6'}
    missing = required - copied
    if missing:
        raise SystemExit(f"PySide6 Addons wheel missing OpenGL pieces: {sorted(missing)}")
    print('Vitalux OpenGL Qt runtime bundled without replacing core Qt packages.')


if __name__ == '__main__':
    main()
