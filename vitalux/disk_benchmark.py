"""Storage benchmark using real fio with defined profiles and JSON metrics.

Temporary benchmark files are created on a selected writable filesystem.
Existing files or raw block devices are never passed to fio.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import threading
import time

MIB = 1024 * 1024


@dataclass(frozen=True)
class TestSpec:
    pattern: str  # seq or rand
    block_kib: int
    depth: int
    threads: int = 1

    def __post_init__(self):
        if self.pattern not in ("seq", "rand"):
            raise ValueError("Testart muss seq oder rand sein")
        if self.block_kib not in (4, 8, 16, 64, 128, 256, 512, 1024):
            raise ValueError("Ungültige Blockgröße")
        if not (1 <= self.depth <= 64 and 1 <= self.threads <= 16):
            raise ValueError("Ungültige Queue Depth oder Threadzahl")

    @property
    def name(self):
        prefix = "SEQ" if self.pattern == "seq" else "RND"
        block = "1M" if self.block_kib == 1024 else f"{self.block_kib}K"
        return f"{prefix}{block} Q{self.depth}T{self.threads}"


PROFILES = {
    "Standard": (
        TestSpec("seq", 1024, 8, 1), TestSpec("seq", 1024, 1, 1),
        TestSpec("rand", 4, 32, 1), TestSpec("rand", 4, 1, 1),
    ),
    "Peak": (TestSpec("seq", 1024, 8, 1), TestSpec("rand", 4, 32, 1)),
    "Real World": (TestSpec("seq", 1024, 1, 1), TestSpec("rand", 4, 1, 1)),
}
# Presets: Standard and NVMe SSD, with preserved fio parameters.
# Standard is also the default preset for Peak, where random Q32T1 is used.
NVME_SSD_PROFILES = {
    "Standard": (TestSpec("seq", 1024, 8, 1), TestSpec("seq", 128, 32, 1),
                 TestSpec("rand", 4, 32, 16), TestSpec("rand", 4, 1, 1)),
    "Peak": (TestSpec("seq", 1024, 8, 1), TestSpec("rand", 4, 32, 16)),
    "Real World": PROFILES["Real World"],
}


def get_profile_tests(profile, preset='Standard'):
    if preset not in ('Standard', 'NVMe SSD'):
        raise ValueError('Unbekannte Benchmark-Voreinstellung')
    table = PROFILES if preset == 'Standard' else NVME_SSD_PROFILES
    return table[profile]

TESTS = PROFILES["Standard"]
ALLOWED_SIZES = (64, 128, 256, 512, 1024, 2048, 4096)
ALLOWED_RUNS = (1, 3, 5, 9)


class BenchmarkCancelled(Exception):
    pass


class FioUnavailable(RuntimeError):
    pass


def app_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def bundled_fio_candidates():
    """Prefer the genuine bundled fio, never the old Vitalux benchmark."""
    return [os.path.join(app_root(), 'bin', 'fio')]



def _validated_engine(argv, source, *, timeout=12):
    """Probe fio by its *actual* version, not by executable name.

    The unrelated Python 'fio' console script (Fiona) is not the Flexible IO
    Tester. Avoid accidentally using it.
    """
    try:
        probe = subprocess.run([*argv, '--version'], capture_output=True,
                               text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    version = probe.stdout.strip()
    match = re.fullmatch(r'fio-(\d+)\.(\d+)(?:\.(\d+))?.*', version)
    if probe.returncode != 0 or not match or (int(match[1]), int(match[2])) < (3, 1):
        return None
    return {'path': argv[0], 'argv': argv, 'source': source, 'version': version}


def fio_source_info():
    """Use exactly the fio binary distributed with Vitalux.

    Never silently switch to a host fio version: that changes benchmark
    comparability and breaks the promised offline portable behavior.
    """
    for candidate in bundled_fio_candidates():
        path = os.path.abspath(candidate)
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return _validated_engine([path], 'bundled')
    return None


def detect_fio():
    info = fio_source_info()
    if not info:
        return None
    argv = info['argv']
    return argv[0] if len(argv) == 1 else argv


def resolve_target(mountpoint, directory):
    mountpoint = os.path.realpath(os.path.abspath(mountpoint))
    directory = os.path.realpath(os.path.abspath(directory))
    if not os.path.isdir(mountpoint) or not os.path.ismount(mountpoint):
        raise ValueError("Die ausgewählte Partition ist nicht mehr eingehängt.")
    if not os.path.isdir(directory):
        raise ValueError("Der Testordner existiert nicht.")
    if os.stat(mountpoint).st_dev != os.stat(directory).st_dev:
        raise ValueError("Testordner und Partition liegen auf unterschiedlichen Dateisystemen.")
    if not os.access(directory, os.W_OK | os.X_OK):
        raise PermissionError("Der Testordner ist nicht beschreibbar.")
    return directory


def _notify(progress, row, kind, value, message=""):
    if progress:
        progress(row, kind, value, message)


def _stop_process(proc):
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            proc.kill()
        proc.wait(timeout=2)


def _run_process(args, cancel, on_tick=None, clock=time.monotonic):
    if cancel.is_set():
        raise BenchmarkCancelled()
    with tempfile.TemporaryFile(mode='w+t', encoding='utf-8') as out, tempfile.TemporaryFile(mode='w+t', encoding='utf-8') as err:
        proc = subprocess.Popen(args, stdout=out, stderr=err, text=True, start_new_session=True)
        start = clock()
        try:
            while proc.poll() is None:
                if cancel.is_set():
                    _stop_process(proc)
                    raise BenchmarkCancelled()
                if on_tick:
                    on_tick(clock() - start)
                cancel.wait(0.15)
            if cancel.is_set():
                raise BenchmarkCancelled()
            out.seek(0); err.seek(0)
            stdout, stderr = out.read(), err.read()
            if proc.returncode != 0:
                raise RuntimeError('Benchmark: ' + (stderr.strip() or stdout.strip() or f'Exit-Code {proc.returncode}')[-1200:])
            return stdout
        finally:
            if proc.poll() is None:
                _stop_process(proc)


def fio_args(executable, filename, test, mode, size_mib, duration=5, direct=True,
             prepare=False, test_data='random', refill=False, mix_read=70):
    """Produce fio parameters (runtime is a *limit*).

    Crucial: do NOT set --time_based. fio stops at filesize OR runtime,
    whichever arrives first. Setting time_based can inflate/repeat workloads.
    """
    if mode not in ('read', 'write'):
        raise ValueError('Modus muss read oder write sein')
    if test_data not in ('random', 'zeros'):
        raise ValueError('Ungültige Testdaten')
    if prepare:
        return [*(executable if isinstance(executable, (list, tuple)) else [executable]), '--output-format=json', '--create_only=1',
                f'--filename={filename}', f'--size={size_mib}m',
                f'--zero_buffers={int(test_data == "zeros")}', '--name=prepare']
    rw = mode if test.pattern == 'seq' else 'rand' + mode
    return [*(executable if isinstance(executable, (list, tuple)) else [executable]), '--output-format=json', '--ioengine=libaio', '--randrepeat=0',
            f'--refill_buffers={int(refill)}', '--end_fsync=1', f'--direct={int(direct)}',
            f'--rwmixread={mix_read}', f'--filename={filename}', f'--name={rw}',
            f'--size={size_mib}m', f'--zero_buffers={int(test_data == "zeros")}',
            f'--bs={test.block_kib}k', f'--runtime={duration}', f'--rw={rw}',
            f'--iodepth={test.depth}', f'--numjobs={test.threads}', '--group_reporting']


def parse_fio_result(output, mode):
    """Use fio's kB/s and completion latency as returned by the engine."""
    try:
        data = json.loads(output)
        stats = data['jobs'][0]
        if stats.get('error', 0) != 0:
            raise ValueError('fio job returned an I/O error')
        measurements = stats[mode]
        # fio bw is in KiB/s; the UI uses kB/s divided by 1000.
        # Fallback is present for fio mock/custom output reporting only bw_bytes.
        bw_kib = measurements.get('bw')
        if bw_kib is not None:
            mbps = float(bw_kib) / 1000.0
        else:
            mbps = float(measurements['bw_bytes']) / 1_000_000.0
        iops = float(measurements['iops'])
        lat = measurements.get('clat_ns', {}).get('mean')
        latency_us = float(lat) / 1000.0 if lat is not None else None
        if mbps < 0 or iops < 0 or (latency_us is not None and latency_us < 0):
            raise ValueError('Ungültiger Messwert')
        return {'mbps': mbps, 'iops': iops, 'latency_us': latency_us}
    except (KeyError, ValueError, TypeError, IndexError, OverflowError) as exc:
        raise RuntimeError(f'fio hat kein gültiges {mode}-Ergebnis geliefert.') from exc


def _aggregate_results(values, profile='Standard'):
    """Average Default runs, and select best results for Peak/Real World."""
    if not values:
        raise ValueError('Kein Messwert')
    best = profile in ('Peak', 'Real World')
    aggregate = max if best else lambda numbers: sum(numbers) / len(numbers)
    return {'mbps': aggregate([v['mbps'] for v in values]),
            'iops': aggregate([v['iops'] for v in values]),
            'latency_us': ((min if best else aggregate)([v['latency_us'] for v in values if v['latency_us'] is not None])
                           if any(v['latency_us'] is not None for v in values) else None),
            'passes': len(values)}

# Kept for compatibility with older helper imports.
_average_results = _aggregate_results


def run_benchmark(mountpoint, directory, size_mib=1024, runs=5, cancel=None,
                  progress=None, *, tests=None, duration=5, interval=5,
                  direct=True, selected_row=None, executable=None,
                  profile='Standard', test_data='random', refill=False):
    cancel = cancel if cancel is not None else threading.Event()
    tests = tuple(tests) if tests is not None else PROFILES.get(profile, TESTS)
    if not tests or any(not isinstance(t, TestSpec) for t in tests):
        raise ValueError('Ungültiges Testprofil')
    if size_mib not in ALLOWED_SIZES or runs not in ALLOWED_RUNS:
        raise ValueError('Ungültige Dateigröße oder Durchläufe')
    if duration not in (1, 3, 5, 10, 15, 30, 60) or interval not in (0, 1, 3, 5, 10):
        raise ValueError('Ungültige Messzeit oder Intervall')
    if profile not in (*PROFILES.keys(), 'Benutzerdefiniert'):
        raise ValueError('Ungültiges Profil')
    if test_data not in ('random', 'zeros'):
        raise ValueError('Ungültiger Datentyp')
    if selected_row is not None and not (0 <= selected_row < len(tests)):
        raise ValueError('Ungültiger Testindex')

    directory = resolve_target(mountpoint, directory)
    executable = executable or detect_fio()
    if not executable:
        raise FioUnavailable('Die fio-Engine ist nicht verfügbar. Prüfe die Plattform und Bibliotheken '
                             'mit ./Portable-pruefen.sh oder ./bin/fio --version.')
    free = shutil.disk_usage(directory).free
    required = size_mib * MIB + max(128 * MIB, size_mib * MIB // 10)
    if free < required:
        raise OSError(f'Nicht genügend Platz: mindestens {required // MIB} MiB erforderlich.')

    selected = [(i, t) for i, t in enumerate(tests) if selected_row is None or selected_row == i]
    # Complete suite: all reads first, then all writes. Single-row tests
    # likewise perform read followed by write.
    groups = [(row, t, mode) for mode in ('read', 'write') for row, t in selected]
    jobs_total = len(groups) * runs
    jobs_completed = intervals_completed = 0
    total_work = jobs_total * duration + max(0, len(groups) - 1) * interval
    last_percent = 0.0

    def phase(row, text, stage='test', elapsed=0.0):
        nonlocal last_percent
        base = jobs_completed * duration + intervals_completed * interval
        length = duration if stage == 'test' else interval if stage == 'interval' else 0.0
        last_percent = max(last_percent, min(99.9, 100 * (base + min(max(0.0, elapsed), length)) / max(1, total_work)))
        _notify(progress, row, 'phase', {'completed': jobs_completed, 'total': jobs_total,
                                         'elapsed': elapsed, 'duration': length, 'stage': stage,
                                         'percent': last_percent}, text)

    with tempfile.TemporaryDirectory(prefix='vitalux-benchmark-', dir=directory) as tdir:
        filename = os.path.join(tdir, 'benchmark.bin')
        # CoW avoidance is best-effort and on the new empty directory, not on
        # existing files. Avoid syswide drop_caches without explicit polkit.
        try:
            import fcntl, struct
            fd = os.open(tdir, os.O_RDONLY | os.O_DIRECTORY)
            try:
                flags = bytearray(4)
                fcntl.ioctl(fd, 0x80086601, flags, True)
                oldflags, = struct.unpack('I', flags)
                fcntl.ioctl(fd, 0x40086602, struct.pack('I', oldflags | 0x00800000))
            finally:
                os.close(fd)
        except (OSError, ImportError, ValueError):
            pass
        phase(-1, 'Bereite temporäre Testdatei mit fio vor …', 'preparing')
        _run_process(fio_args(executable, filename, tests[0], 'write', size_mib,
                              prepare=True, test_data=test_data), cancel)
        for group_index, (row, test, mode) in enumerate(groups):
            measurements = []
            for repetition in range(1, runs + 1):
                status = f'{test.name}: {mode.upper()} · Durchlauf {repetition}/{runs}'
                phase(row, status)
                out = _run_process(fio_args(executable, filename, test, mode, size_mib,
                                            duration=duration, direct=direct,
                                            test_data=test_data, refill=refill),
                                   cancel, on_tick=lambda seconds, r=row, msg=status:
                                   phase(r, msg, 'test', seconds))
                measurements.append(parse_fio_result(out, mode))
                result = _aggregate_results(measurements, profile)
                jobs_completed += 1
                phase(row, status)
                _notify(progress, row, mode, result, status)
                _notify(progress, row, 'pass', {'completed': jobs_completed, 'total': jobs_total,
                                               'percent': last_percent, 'mode': mode,
                                               'result': result}, '')
            if group_index < len(groups) - 1 and interval:
                started = time.monotonic()
                while True:
                    elapsed = time.monotonic() - started
                    phase(row, f'Intervall {interval}s …', 'interval', elapsed)
                    if elapsed >= interval:
                        break
                    if cancel.wait(min(.15, interval - elapsed)):
                        raise BenchmarkCancelled()
                intervals_completed += 1
        return ' '.join(executable) if isinstance(executable, (list, tuple)) else executable
