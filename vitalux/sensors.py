"""Datenquellen (ohne Qt). collect() liefert einen kompletten Schnappschuss."""
import functools
import getpass
import glob
import os
import platform
import re
import shlex
import shutil
import socket
import subprocess
import time

import psutil

from .i18n import tr
from . import extended, monitor_extra

_last = {}


def _rate(key, value):
    now = time.monotonic()
    prev = _last.get(key)
    _last[key] = (value, now)
    if not prev or now - prev[1] <= 0:
        return 0.0
    return max(0.0, (value - prev[0]) / (now - prev[1]))


def _read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    except OSError:
        return None


def _num(s, mult=1):
    try:
        return float(s) * mult
    except (ValueError, TypeError):
        return None


def _run(*cmd, timeout=2):
    try:
        return subprocess.run(list(cmd), capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception:
        return ""


def prime():
    psutil.cpu_percent(interval=None, percpu=True)
    psutil.net_io_counters()
    psutil.disk_io_counters()


def collect():
    net_total = psutil.net_io_counters()
    dio = psutil.disk_io_counters()
    sensor_data = extended.sensor_info()
    return {
        "cpu": cpu_info(),
        "ram": ram_info(),
        "disks": disk_info(),
        "gpus": gpu_info(),
        "net": network_info(net_total),
        "io": {"read": _rate("dr", dio.read_bytes), "write": _rate("dw", dio.write_bytes)} if dio else {"read": 0, "write": 0},
        "sensors": sensor_data,
        "app_resources": monitor_extra.app_resources(),
        "uptime": time.time() - psutil.boot_time(),
    }


# ---------------------------------------------------------------- CPU
@functools.lru_cache(maxsize=1)
def _cpu_model():
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as f:
            for line in f:
                if line.startswith("model name"):
                    return re.sub(r"\s+", " ", line.split(":", 1)[1].strip())
    except OSError:
        pass
    return platform.processor() or "Unbekannter Prozessor"


def _cpu_temp():
    try:
        temps = psutil.sensors_temperatures()
    except Exception:
        return None
    for key in ("coretemp", "k10temp", "zenpower", "cpu_thermal", "acpitz"):
        entries = temps.get(key)
        if not entries:
            continue
        for e in entries:
            if e.label in ("Package id 0", "Tctl", "Tdie"):
                return e.current
        return entries[0].current
    return None


def cpu_info():
    freq = psutil.cpu_freq()
    try:
        load = os.getloadavg()
    except OSError:
        load = (0, 0, 0)
    per_core = psutil.cpu_percent(interval=None, percpu=True)
    return {
        "model": _cpu_model(),
        "usage": sum(per_core) / len(per_core) if per_core else 0.0,
        "per_core": per_core,
        "cores": psutil.cpu_count(logical=False) or 0,
        "threads": psutil.cpu_count(logical=True) or 0,
        "freq": freq.current if freq else None,
        "freq_max": freq.max if freq and freq.max else None,
        "temp": _cpu_temp(),
        "power": monitor_extra.cpu_package_power(),
        "load": load,
    }


# ---------------------------------------------------------------- RAM
def ram_info():
    vm = psutil.virtual_memory()
    sw = psutil.swap_memory()
    return {
        "total": vm.total,
        "used": vm.total - vm.available,
        "available": vm.available,
        "cached": getattr(vm, "cached", 0),
        "buffers": getattr(vm, "buffers", 0),
        "percent": (vm.total - vm.available) / vm.total * 100 if vm.total else 0,
        "swap_used": sw.used,
        "swap_total": sw.total,
        "swap_percent": sw.percent,
    }


# ---------------------------------------------------------------- Laufwerke
def disk_info():
    result, seen = [], set()
    skip_fs = ("squashfs", "tmpfs", "devtmpfs", "overlay", "efivarfs", "ramfs", "iso9660")
    for p in psutil.disk_partitions(all=False):
        if p.device in seen or p.fstype in skip_fs or p.mountpoint.startswith(("/snap", "/var/lib/docker")):
            continue
        try:
            u = psutil.disk_usage(p.mountpoint)
        except OSError:
            continue
        seen.add(p.device)
        result.append({"mount": p.mountpoint, "device": p.device, "fstype": p.fstype,
                       "used": u.used, "total": u.total, "percent": u.percent})
    result.sort(key=lambda d: (d["mount"] != "/", d["mount"]))
    return result


def drives():
    out = []
    for path in sorted(glob.glob("/sys/block/*")):
        name = os.path.basename(path)
        if name.startswith(("loop", "ram", "zram", "dm-", "sr", "md", "fd")):
            continue
        size = _read(os.path.join(path, "size"))
        if not size or not size.isdigit() or int(size) == 0:
            continue
        model = _read(os.path.join(path, "device", "model")) or ""
        rota = _read(os.path.join(path, "queue", "rotational"))
        kind = "NVMe" if name.startswith("nvme") else "SD/eMMC" if name.startswith("mmcblk") else \
            "SSD" if rota == "0" else "HDD"
        out.append({"name": name, "model": model, "size": int(size) * 512, "kind": kind})
    return out


# ---------------------------------------------------------------- GPU
@functools.lru_cache(maxsize=1)
def _lspci_names():
    names = {}
    if not shutil.which("lspci"):
        return names
    out = _run("lspci", "-mm", timeout=3)
    for line in out.splitlines():
        try:
            parts = shlex.split(line)
        except ValueError:
            continue
        if len(parts) >= 4 and any(k in parts[1] for k in ("VGA", "3D controller", "Display controller")):
            m = re.search(r"\[(.+)\]", parts[3])
            names[parts[0]] = m.group(1) if m else parts[3]
    return names


def _name_for_slot(slot, fallback):
    for k, v in _lspci_names().items():
        if slot and slot.endswith(k):
            return v
    return fallback


def _nvidia_gpus():
    if not shutil.which("nvidia-smi"):
        return []
    q = "name,driver_version,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw,fan.speed,clocks.gr,clocks.mem"
    out = _run("nvidia-smi", f"--query-gpu={q}", "--format=csv,noheader,nounits")
    gpus = []
    for line in out.strip().splitlines():
        p = [x.strip() for x in line.split(",")]
        if len(p) < 10:
            continue
        gpus.append({"vendor": "NVIDIA", "name": p[0], "driver": p[1], "usage": _num(p[2]),
                     "vram_used": _num(p[3], 1048576), "vram_total": _num(p[4], 1048576),
                     "temp": _num(p[5]), "power": _num(p[6]), "fan": _num(p[7]),
                     "clock": _num(p[8]), "clock_mem": _num(p[9]), "hotspot": None,
                     "fan_rpm": None, "voltage": None, "pcie_current": None,
                     "pcie_max": None, "sensor_source": "nvidia-smi"})
    return gpus


def _drm_gpus(have_nvidia):
    gpus = []
    vendors = {"0x1002": "AMD", "0x8086": "Intel", "0x10de": "NVIDIA"}
    for card in sorted(glob.glob("/sys/class/drm/card[0-9]")):
        dev = os.path.join(card, "device")
        vendor = vendors.get(_read(os.path.join(dev, "vendor")))
        if not vendor or (vendor == "NVIDIA" and have_nvidia):
            continue
        uevent = _read(os.path.join(dev, "uevent")) or ""
        m = re.search(r"PCI_SLOT_NAME=(\S+)", uevent)
        name = overview_gpu_name(_name_for_slot(m.group(1) if m else "", f"{vendor} Grafik"))
        hw = glob.glob(os.path.join(dev, "hwmon", "hwmon*"))
        temp = power = None
        if hw:
            t = _read(os.path.join(hw[0], "temp1_input"))
            temp = float(t) / 1000 if t and t.isdigit() else None
            pw = _read(os.path.join(hw[0], "power1_average")) or _read(os.path.join(hw[0], "power1_input"))
            power = float(pw) / 1e6 if pw and pw.isdigit() else None
        # These read-only sysfs values are provided by the kernel; do not use
        # optional overclocking drivers, services or elevated permissions.
        voltage = None
        if hw:
            millivolts = _num(_read(os.path.join(hw[0], "in0_input")))
            if millivolts is not None and 100 <= millivolts <= 2500:
                voltage = millivolts
        from .monitor_insights import pcie_link
        pcie_now, pcie_max = pcie_link(
            _read(os.path.join(dev, "current_link_speed")),
            _read(os.path.join(dev, "current_link_width")),
            _read(os.path.join(dev, "max_link_speed")),
            _read(os.path.join(dev, "max_link_width")),
        )
        busy = _read(os.path.join(dev, "gpu_busy_percent"))
        used, total = _read(os.path.join(dev, "mem_info_vram_used")), _read(os.path.join(dev, "mem_info_vram_total"))
        extra = extended.drm_extra(dev)
        gpus.append({"vendor": vendor, "name": name, "driver": extra["driver"],
                     "usage": _num(busy), "vram_used": _num(used), "vram_total": _num(total),
                     "temp": extra["edge"] if extra["edge"] is not None else temp,
                     "hotspot": extra["hotspot"], "power": power, "fan": extra["fan_percent"],
                     "fan_rpm": extra["fan_rpm"], "clock": extra["clock"],
                     "clock_mem": extra["clock_mem"], "voltage": voltage,
                     "pcie_current": pcie_now, "pcie_max": pcie_max,
                     "sensor_source": "Linux DRM / sysfs"})
    return gpus


def gpu_info():
    nv = _nvidia_gpus()
    return nv + _drm_gpus(bool(nv))


@functools.lru_cache(maxsize=16)
def overview_gpu_name(reported):
    """Prefer an unambiguous GPU name reported by the graphics stack.

    A shared PCI ID must not be guessed into an exact model. No extra package
    is needed and a missing vulkaninfo/glxinfo leaves the reported name intact.
    """
    reported = str(reported or '').strip()
    if '/' not in reported or not any(k in reported.lower() for k in ('radeon', 'amd', 'rx 90')):
        return reported
    for command in (('vulkaninfo', '--summary'), ('glxinfo', '-B')):
        if not shutil.which(command[0]):
            continue
        output = _run(*command, timeout=2)
        for line in output.splitlines():
            if any(k in line.lower() for k in ('devicename', 'device name', 'opengl renderer')):
                match = re.search(r'\b(?:AMD\s+)?Radeon\s+RX\s+\d{4}\s*(?:XT|GRE|XTX)?\b', line, re.I)
                if match and '/' not in match.group():
                    return 'AMD ' + re.sub(r'^(AMD\s+)', '', match.group(), flags=re.I)
    return reported


# ---------------------------------------------------------------- Netzwerk
def _pick_primary_iface(stats, addrs):
    route_name = extended.net_static_details()["route_interface"]
    if route_name in stats and stats[route_name].isup:
        return route_name
    candidates = []
    for name, st in stats.items():
        if not st.isup or name.startswith(("lo", "virbr", "docker", "veth", "br-")):
            continue
        ipv4 = next((a.address for a in addrs.get(name, []) if getattr(a, 'family', None) == socket.AF_INET), None)
        score = (1 if ipv4 else 0, st.speed or 0, -len(name))
        candidates.append((score, name))
    return max(candidates)[1] if candidates else None


def network_info(total=None):
    total = total or psutil.net_io_counters()
    stats = psutil.net_if_stats()
    addrs = psutil.net_if_addrs()
    pernic = psutil.net_io_counters(pernic=True)
    primary = _pick_primary_iface(stats, addrs)
    route = extended.net_static_details()
    interfaces = []
    for name in sorted(stats):
        if name.startswith(("lo",)):
            continue
        st = stats[name]
        addr = addrs.get(name, [])
        ipv4 = next((a.address for a in addr if getattr(a, 'family', None) == socket.AF_INET), None)
        ipv6 = next((a.address for a in addr if getattr(a, 'family', None) == socket.AF_INET6), None)
        mac_families = (getattr(psutil, 'AF_LINK', None), getattr(socket, 'AF_PACKET', None))
        mac = next((a.address for a in addr if getattr(a, 'family', None) in mac_families), None)
        ctr = pernic.get(name)
        interfaces.append({
            "name": name,
            "isup": st.isup,
            "speed": st.speed,
            "mtu": st.mtu,
            "ipv4": ipv4,
            "ipv6": ipv6,
            "mac": mac,
            "bytes_recv": ctr.bytes_recv if ctr else 0,
            "bytes_sent": ctr.bytes_sent if ctr else 0,
        })
    active = next((x for x in interfaces if x["name"] == primary), interfaces[0] if interfaces else None)
    return {
        "down": _rate("rx", total.bytes_recv if total else 0),
        "up": _rate("tx", total.bytes_sent if total else 0),
        "total_down": total.bytes_recv if total else 0,
        "total_up": total.bytes_sent if total else 0,
        "interfaces": interfaces,
        "primary": active,
        "gateway": route["gateway"],
        "dns": route["dns"],
        "host": socket.gethostname(),
    }


# ---------------------------------------------------------------- System helpers
@functools.lru_cache(maxsize=1)
def _plasma_version():
    out = _run("plasmashell", "--version")
    m = re.search(r"(\d+(?:\.\d+)+)", out)
    if m:
        return m.group(1)
    return os.environ.get("KDE_SESSION_VERSION") or "–"


@functools.lru_cache(maxsize=1)
def _kwin_version():
    for cmd in (("kwin_wayland", "--version"), ("kwin_x11", "--version"), ("kwin", "--version")):
        out = _run(*cmd)
        m = re.search(r"(\d+(?:\.\d+)+)", out)
        if m:
            return m.group(1)
    return "–"


@functools.lru_cache(maxsize=1)
def _qt_kf_versions():
    for exe in ("kded6", "kbuildsycoca6", "kded5", "kbuildsycoca5"):
        out = _run(exe, "--version")
        if out:
            qt = re.search(r"Qt:\s*([\d.]+)", out)
            kf = re.search(r"KDE Frameworks:\s*([\d.]+)", out)
            return (qt.group(1) if qt else "–", kf.group(1) if kf else "–")
    return ("–", "–")


@functools.lru_cache(maxsize=1)
def _mesa_version():
    for cmd in (("glxinfo", "-B"), ("eglinfo", "-B"), ("vulkaninfo", "--summary")):
        if not shutil.which(cmd[0]):
            continue
        out = _run(*cmd, timeout=4)
        m = re.search(r"Mesa\s+([\d.]+)", out)
        if m:
            return m.group(1)
    # Prefer the distro package database when GL/Vulkan CLI tools are absent.
    for cmd in (("rpm", "-q", "--qf", "%{VERSION}\n", "Mesa"),
                ("rpm", "-q", "--qf", "%{VERSION}\n", "Mesa-libGL1"),
                ("pacman", "-Q", "mesa"),
                ("dpkg-query", "-W", "-f=${Version}", "libgl1-mesa-dri")):
        if not shutil.which(cmd[0]):
            continue
        out = _run(*cmd)
        m = re.search(r"(\d+(?:\.\d+)+)", out)
        if m and not out.lower().startswith(('package ', 'error:')):
            return m.group(1)
    return "–"


# ---------------------------------------------------------------- System
@functools.lru_cache(maxsize=1)
def system_static():
    dmi = lambda n: _read(f"/sys/class/dmi/id/{n}") or "–"
    qt_ver, kf_ver = _qt_kf_versions()
    return {
        "kernel": platform.release(), "arch": platform.machine(), "host": platform.node(),
        "user": getpass.getuser(),
        "desktop": os.environ.get("XDG_CURRENT_DESKTOP", "–"),
        "session": os.environ.get("XDG_SESSION_TYPE", "–"),
        "vendor": dmi("sys_vendor"), "product": dmi("product_name"),
        "board": f"{dmi('board_vendor')} {dmi('board_name')}".replace("– ", "").strip(),
        "bios": dmi("bios_version"),
        "plasma": _plasma_version(),
        "kwin": _kwin_version(),
        "qt_runtime": qt_ver,
        "frameworks": kf_ver,
        "mesa": _mesa_version(),
    }


# ---------------------------------------------------------------- Formatierung
def fmt_bytes(n, base=1024):
    if n is None:
        return "–"
    units = ("B", "KB", "MB", "GB", "TB", "PB")
    for i, u in enumerate(units):
        if n < base or i == len(units) - 1:
            return f"{int(n)} B" if i == 0 else f"{n:.1f} {u}"
        n /= base


def fmt_rate(n):
    return fmt_bytes(n) + "/s"


def fmt_duration(sec):
    sec = int(sec)
    d, sec = divmod(sec, 86400)
    h, sec = divmod(sec, 3600)
    m = sec // 60
    return (f"{d} {tr('T')} " if d else "") + f"{h} {tr('Std')} {m} {tr('Min')}"
