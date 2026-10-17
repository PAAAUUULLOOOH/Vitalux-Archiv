"""Vitalux release updates via GitHub: ZIP installation or atomic AppImage replacement."""
import json
import hashlib
import shlex
import subprocess
import time
import os
import re
import shutil
import tempfile
import urllib.error
import urllib.request
import zipfile
import ssl
import socket
from pathlib import PurePosixPath
import stat

from . import APP_NAME, APP_ID, __version__, settings
from .i18n import tr

DEFAULT_REPO = "PAAAUUULLOOOH/Vitalux"  # Feste, offizielle Updatequelle; keine frei eingebbaren URLs.
HEADERS = {"User-Agent": f"{APP_NAME}-Updater", "Accept": "application/vnd.github+json"}
SKIP = {".venv", ".libs", ".backup", f"{APP_ID}.log", f"{APP_ID}.log.old", ".qtcheck", "__pycache__", ".git"}


def app_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _ver(v):
    return tuple(int(x) for x in re.findall(r"\d+", v or ""))


# The bundled Python/OpenSSL runtime may use Debian's CA path on non-Debian
# systems (e.g. openSUSE). Trust the host's actual CA bundle, never disable TLS.
CA_BUNDLES = (
    "/etc/ssl/certs/ca-certificates.crt",       # Debian, Ubuntu, Arch, Fedora
    "/etc/ssl/ca-bundle.pem",                  # openSUSE
    "/var/lib/ca-certificates/ca-bundle.pem", # openSUSE
    "/etc/pki/trust/extracted/pem/tls-ca-bundle.pem", # Fedora/openSUSE
    "/etc/pki/tls/certs/ca-bundle.crt",       # RHEL
    "/etc/ssl/cert.pem",                     # Other Linux systems
)


def _tls_context():
    """Load a valid OS trust store for the embedded Python interpreter."""
    # Honor the user's explicit override when it names a real certificate file.
    explicit = os.environ.get("SSL_CERT_FILE")
    paths = (explicit,) + CA_BUNDLES if explicit else CA_BUNDLES
    for path in paths:
        if path and os.path.isfile(path):
            try:
                return ssl.create_default_context(cafile=path)
            except (OSError, ssl.SSLError):
                continue
    # Allows OpenSSL to use a CA directory (and respects SSL_CERT_DIR).
    return ssl.create_default_context()


def _github_request(request, timeout):
    return urllib.request.urlopen(request, timeout=timeout, context=_tls_context())


def _get_release():
    req = urllib.request.Request(
        f"https://api.github.com/repos/{DEFAULT_REPO}/releases/latest", headers=HEADERS)
    with _github_request(req, timeout=12) as response:
        return json.load(response)


def check():
    """Only releases from the official GitHub repo with the exact app binary."""
    repo = DEFAULT_REPO
    try:
        data = _get_release()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"ok": False, "error": "Noch keine Vitalux-Version über GitHub Releases veröffentlicht."}
        return {"ok": False, "error": f"GitHub: HTTP {e.code}"}
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        reason = getattr(exc, "reason", exc)
        if isinstance(reason, ssl.SSLCertVerificationError):
            message = ("GitHub-Zertifikat konnte nicht geprüft werden. "
                       "Bitte Systemzeit und CA-Zertifikate prüfen. "
                       f"Details: {reason}")
        elif isinstance(reason, socket.gaierror):
            message = f"GitHub-DNS-Auflösung fehlgeschlagen: {reason}"
        else:
            message = f"GitHub ist nicht erreichbar: {reason}"
        return {"ok": False, "error": str(message)[:320]}
    except (ValueError, TypeError):
        return {"ok": False, "error": tr("Unerwartete Antwort von GitHub.")}

    tag = str(data.get("tag_name", ""))
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:\.\d+)?", tag):
        return {"ok": False, "error": "Ungültige Versionsangabe bei GitHub."}
    is_appimage = bool(os.environ.get("APPIMAGE"))
    # A current/older release is not an update even while its artifacts build.
    if _ver(tag) <= _ver(__version__):
        return {"ok": True, "latest": tag.lstrip("v"), "notes": "", "url": "",
                "sha256": "", "kind": "appimage" if is_appimage else "zip", "newer": False}
    # Neuer Standardname ohne „Portabel“; ältere Releases bleiben kompatibel.
    suffixes = ("-x86_64.AppImage",) if is_appimage else (
        "-linux-x86_64.zip", "-linux-x86_64-Portabel.zip")
    expected_names = [f"Vitalux-{tag}{suffix}" for suffix in suffixes]
    item = next((a for name in expected_names for a in data.get("assets", [])
                 if a.get("name") == name), None)
    expected_name = str(item.get("name", "")) if item else expected_names[0]
    if not item:
        # When a release was just published, the AppImage may still be building.
        return {"ok": False, "error":
                "Das offizielle Vitalux-Update wird auf GitHub noch erstellt oder ist nicht verfügbar."}
    download_url = str(item.get('browser_download_url', ''))
    expected_url = f"https://github.com/{repo}/releases/download/{tag}/{expected_name}"
    if download_url != expected_url:
        return {"ok": False, "error": "Ungültige Adresse der Vitalux-Release-Datei."}
    checksum = str(item.get('digest') or '')
    if not re.fullmatch(r'sha256:[0-9a-fA-F]{64}', checksum):
        return {"ok": False, "error": 'GitHub Release liefert keine SHA-256-Prüfsumme für die Programmdatei.'}
    return {"ok": True, "latest": tag.lstrip('vV'), "notes": (data.get('body') or '').strip(),
            "url": download_url, "sha256": checksum.split(':', 1)[1].lower(),
            "kind": "appimage" if is_appimage else "zip", "newer": _ver(tag) > _ver(__version__)}


def _download_verified(url, output_path, sha256, progress, download_limit):
    """Stream to disk with size cap and SHA-256 check (digest taken from GitHub Releases API)."""
    if not re.fullmatch('[0-9a-fA-F]{64}', sha256 or ''):
        raise RuntimeError('SHA-256-Prüfsumme fehlt. Update aus Sicherheitsgründen abgebrochen.')
    digest = hashlib.sha256()
    length = 0
    request = urllib.request.Request(url, headers={'User-Agent': HEADERS['User-Agent']})
    with _github_request(request, timeout=45) as response, open(output_path, 'wb') as f:
        if response.geturl().split(':', 1)[0] != 'https':
            raise RuntimeError('Update-Download ohne HTTPS abgebrochen.')
        total = int(response.headers.get('Content-Length') or '0')
        if total > download_limit:
            raise RuntimeError('Updatepaket überschreitet Größenlimit.')
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            length += len(chunk)
            if length > download_limit:
                raise RuntimeError('Updatepaket überschreitet Größenlimit.')
            f.write(chunk)
            digest.update(chunk)
            if total:
                progress(min(88., 88. * length / total))
        f.flush()
        os.fsync(f.fileno())
    if digest.hexdigest() != sha256.lower():
        raise RuntimeError('Sicherheitsprüfung fehlgeschlagen: SHA-256 stimmt nicht überein.')


def appimage_path():
    return os.environ.get('APPIMAGE') or ''


def _stage_appimage(url, sha256, progress):
    target = os.path.realpath(appimage_path())
    if not target or not os.path.isfile(target):
        raise RuntimeError('Vitalux ist nicht als AppImage gestartet.')
    folder = os.path.dirname(target)
    if not os.access(folder, os.W_OK):
        raise RuntimeError('AppImage liegt in einem schreibgeschützten Ordner. Bitte Vitalux im Benutzerordner installieren.')
    fd, staged = tempfile.mkstemp(prefix='.vitalux-next-', suffix='.AppImage', dir=folder)
    os.close(fd)
    try:
        _download_verified(url, staged, sha256, progress, 900 * 1024 * 1024)
        with open(staged, 'rb') as f:
            head = f.read(11)
        if not head.startswith(b'\x7fELF') or head[8:11] != b'AI\x02':
            raise RuntimeError('Heruntergeladene Datei ist kein gültiges AppImage vom Typ 2.')
        os.chmod(staged, 0o755)
        progress(95.)
        return staged
    except Exception:
        os.unlink(staged)
        raise


def activate_appimage_update(staged):
    """External /bin/sh helper survives unmounting old AppImage and replaces file atomically."""
    target = os.path.realpath(appimage_path())
    if not os.path.isfile(target) or os.path.dirname(staged) != os.path.dirname(target):
        raise RuntimeError('AppImage-Update konnte nicht sicher vorbereitet werden.')
    cache = os.path.join(os.environ.get('XDG_CACHE_HOME') or os.path.expanduser('~/.cache'), 'vitalux')
    os.makedirs(cache, mode=0o700, exist_ok=True)
    fd, script = tempfile.mkstemp(prefix='apply-update-', suffix='.sh', dir=cache)
    q = shlex.quote
    # The current process must exit before the AppImage is switched and reopened.
    script_text = f"""#!/bin/sh
set -eu
oldpid={os.getpid()}
target={q(target)}
staged={q(staged)}
backup={q(target + '.previous')}
state_dir={q(os.path.join(os.environ.get('XDG_STATE_HOME') or os.path.expanduser('~/.local/state'), 'vitalux'))}
version={q(__version__)}
mkdir -p "$state_dir"
stamp() {{
  printf '[%s] [Vitalux v%s] %s\\n' "$(date -Is)" "$version" "$*" >> "$state_dir/restart.log"
}}
for i in $(seq 1 150); do
  if ! kill -0 "$oldpid" 2>/dev/null; then break; fi
  sleep 0.2
done
if kill -0 "$oldpid" 2>/dev/null; then exit 1; fi
if [ ! -f "$staged" ] || [ ! -f "$target" ]; then exit 1; fi
cp -p -- "$target" "${{backup}}.tmp"
mv -f -- "${{backup}}.tmp" "$backup"
mv -f -- "$staged" "$target"
unset APPDIR APPIMAGE LD_LIBRARY_PATH LD_PRELOAD PYTHONHOME PYTHONPATH PYTHONUSERBASE
stamp "Vitalux update activation: old version v$version, launching newly installed AppImage."
# Record even early loader failures in restart.log, with date and source version.
( "$target" --launch 2>&1 | while IFS= read -r line || [ -n "$line" ]; do
    stamp "$line"
  done ) &
"""
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(script_text)
        os.chmod(script, 0o700)
        subprocess.Popen(['/bin/sh', script], start_new_session=True,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        try: os.unlink(script)
        except OSError: pass
        raise



def cleanup_superseded_backups(root=None):
    """Delete only stale update-temp backups, never the latest rollback copy.

    For AppImages, the update helper atomically replaces the single
    Vitalux.AppImage.previous with the immediately preceding version; this
    backup must be kept until a later update or an automatic rollback.
    ZIP updates likewise keep .backup; any abandoned .backup.old from a
    previous interrupted update can be cleaned separately.
    """
    root = os.path.realpath(root or app_root())
    old = os.path.join(root, '.backup.old')
    if os.path.islink(old):
        return False
    if os.path.isdir(old) and os.path.isfile(os.path.join(old, 'metadata.json')):
        shutil.rmtree(old)
        return True
    return False


def _find_root(extracted):
    for dirpath, _dirs, files in os.walk(extracted):
        if "run.sh" in files and os.path.isfile(os.path.join(dirpath, APP_ID, "__main__.py")):
            return dirpath
    return None


def backup_available(root=None):
    root = root or app_root()
    backup = os.path.join(root, '.backup')
    return (os.path.isfile(os.path.join(backup, APP_ID, '__main__.py')) and
            os.path.isfile(os.path.join(backup, 'metadata.json')))


def _stage_backup(root, root_files):
    """Prepare complete previous application + launcher + settings snapshot.

    The previous .backup remains valid until a new snapshot is fully built.
    """
    backup = os.path.join(root, '.backup')
    stage = tempfile.mkdtemp(prefix='.vitalux-backup-stage-', dir=root)
    try:
        shutil.copytree(os.path.join(root, APP_ID), os.path.join(stage, APP_ID),
                        ignore=shutil.ignore_patterns('__pycache__'))
        filesdir = os.path.join(stage, 'root_files')
        os.makedirs(filesdir, exist_ok=True)
        for name in root_files:
            original = os.path.join(root, name)
            if os.path.isfile(original):
                shutil.copy2(original, os.path.join(filesdir, name))
            elif os.path.isdir(original) and not os.path.islink(original):
                shutil.copytree(original, os.path.join(filesdir, name),
                                ignore=shutil.ignore_patterns('__pycache__'))
        if os.path.isfile(settings.PATH):
            shutil.copy2(settings.PATH, os.path.join(stage, 'settings.json'))
        with open(os.path.join(stage, 'metadata.json'), 'w', encoding='utf-8') as f:
            json.dump({'version': __version__, 'root_files': list(root_files),
                       'settings_saved': os.path.isfile(os.path.join(stage, 'settings.json'))}, f)
        old = backup + '.old'
        shutil.rmtree(old, ignore_errors=True)
        if os.path.exists(backup):
            os.replace(backup, old)
        os.replace(stage, backup)
        stage = None
        shutil.rmtree(old, ignore_errors=True)
    finally:
        if stage and os.path.exists(stage):
            shutil.rmtree(stage, ignore_errors=True)


def _install_from_directory(src, root, progress):
    root = os.path.abspath(root)
    pkg = os.path.join(root, APP_ID)
    if not os.path.isdir(pkg):
        raise RuntimeError('Bestehende Vitalux-Installation nicht gefunden.')
    # Preserve launcher/scripts and their last-known-good content for rollback.
    root_files = [name for name in os.listdir(src)
                  if name not in SKIP and name != APP_ID and not name.startswith('.')
                  and not os.path.islink(os.path.join(src, name))]
    staged = tempfile.mkdtemp(prefix='.vitalux-package-', dir=root)
    stage_pkg = os.path.join(staged, APP_ID)
    former = os.path.join(staged, 'former')
    touched = False
    try:
        shutil.copytree(os.path.join(src, APP_ID), stage_pkg, ignore=shutil.ignore_patterns('__pycache__'))
        if not os.path.isfile(os.path.join(stage_pkg, '__main__.py')):
            raise RuntimeError('Update enthält kein ausführbares Vitalux-Modul.')
        _stage_backup(root, root_files)
        progress(89)
        os.replace(pkg, former)
        touched = True
        try:
            os.replace(stage_pkg, pkg)
            for name in root_files:
                source = os.path.join(src, name)
                destination = os.path.join(root, name)
                if os.path.isdir(source):
                    temp_dir = tempfile.mkdtemp(prefix='.vitalux-assets-', dir=root)
                    new_dir = os.path.join(temp_dir, 'new')
                    try:
                        shutil.copytree(source, new_dir)
                        if os.path.isdir(destination):
                            old_dir = os.path.join(temp_dir, 'old')
                            os.replace(destination, old_dir)
                        os.replace(new_dir, destination)
                    finally:
                        shutil.rmtree(temp_dir, ignore_errors=True)
                else:
                    fd, tmp_name = tempfile.mkstemp(prefix='.vitalux-file-', dir=root)
                    os.close(fd)
                    try:
                        shutil.copy2(source, tmp_name)
                        os.replace(tmp_name, destination)
                    finally:
                        if os.path.exists(tmp_name):
                            os.unlink(tmp_name)
            progress(100)
        except Exception:
            if os.path.isdir(pkg):
                shutil.rmtree(pkg)
            os.replace(former, pkg)
            touched = False
            _restore_root_files(root, os.path.join(root, '.backup'))
            raise
    finally:
        # When successful, former is redundant (the persistent backup holds a copy).
        # Never delete a saved former install if the attempted rollback failed.
        if not touched or os.path.isdir(pkg):
            shutil.rmtree(staged, ignore_errors=True)


def _restore_root_files(root, backup):
    try:
        with open(os.path.join(backup, 'metadata.json'), encoding='utf-8') as f:
            files = json.load(f).get('root_files', [])
    except (OSError, ValueError):
        files = []
    for name in files:
        if name in SKIP or '/' in name or name.startswith('.'):
            continue
        original = os.path.join(backup, 'root_files', name)
        destination = os.path.join(root, name)
        if os.path.isfile(original):
            shutil.copy2(original, destination)
        elif os.path.isdir(original):
            if os.path.isdir(destination):
                shutil.rmtree(destination)
            shutil.copytree(original, destination)


def restore_previous(root=None, restore_settings=True):
    """Restore the last pre-update package; optionally restore its settings.

    Call only after confirmation and with no active disk benchmark.
    """
    root = root or app_root()
    if not backup_available(root):
        raise RuntimeError('Keine vorherige Version gesichert.')
    backup = os.path.join(root, '.backup')
    target = os.path.join(root, APP_ID)
    stage = tempfile.mkdtemp(prefix='.vitalux-rollback-', dir=root)
    saved_current = os.path.join(stage, 'current')
    restored = os.path.join(stage, APP_ID)
    try:
        shutil.copytree(os.path.join(backup, APP_ID), restored)
        os.replace(target, saved_current)
        try:
            os.replace(restored, target)
            _restore_root_files(root, backup)
            if restore_settings and os.path.isfile(os.path.join(backup, 'settings.json')):
                os.makedirs(os.path.dirname(settings.PATH), exist_ok=True)
                shutil.copy2(os.path.join(backup, 'settings.json'), settings.PATH)
        except Exception:
            if os.path.isdir(target):
                shutil.rmtree(target)
            os.replace(saved_current, target)
            raise
    finally:
        if os.path.isdir(target):
            shutil.rmtree(stage, ignore_errors=True)


def install(url, root=None, progress=lambda p: None, sha256=None):
    if appimage_path():
        return _stage_appimage(url, sha256, progress)
    root = root or app_root()
    tmp = tempfile.mkdtemp(prefix=f'{APP_ID}-update-')
    try:
        zpath = os.path.join(tmp, 'update.zip')
        _download_verified(url, zpath, sha256, progress, 700 * 1024 * 1024)
        extracted = os.path.join(tmp, 'x')
        with zipfile.ZipFile(zpath) as z:
            members = z.infolist()
            if len(members) > 12000 or sum(item.file_size for item in members) > 1200 * 1024 * 1024:
                raise RuntimeError('Updatepaket ist zu groß.')
            for item in members:
                path = PurePosixPath(item.filename)
                unix_mode = item.external_attr >> 16
                if path.is_absolute() or '..' in path.parts or stat.S_ISLNK(unix_mode) or '\\' in item.filename:
                    raise RuntimeError('Unsicherer Pfad im Updatepaket.')
            z.extractall(extracted)
        progress(85)
        src = _find_root(extracted)
        if not src:
            raise RuntimeError(tr('Das Update-Paket hat eine unbekannte Struktur.'))
        _install_from_directory(src, root, progress)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
