"""Additional optional Linux monitoring. Missing sensors are reported as unavailable."""
import glob
import os
import re
import socket
import struct
import subprocess
import time
from functools import lru_cache

import psutil


def read(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read().strip()
    except (OSError, ValueError):
        return ''


def num(value, divisor=1.0):
    try:
        return float(value) / divisor
    except (ValueError, TypeError, OverflowError):
        return None


def _hwmon(card_device):
    for path in sorted(glob.glob(os.path.join(card_device, 'hwmon', 'hwmon*'))):
        if os.path.isdir(path):
            return path
    return None


def _temp_label_data(hw):
    out = {}
    if not hw:
        return out
    for file in glob.glob(os.path.join(hw, 'temp*_input')):
        prefix = file[:-6]  # cut '_input'
        label = read(prefix + '_label').lower()
        val = num(read(file), 1000)
        if val is not None:
            out[label or os.path.basename(prefix)] = val
    return out


def _freq_active(path):
    data = read(path)
    for line in data.splitlines():
        if '*' in line:
            match = re.search(r'\b(\d+)Mhz\b', line, re.I)
            if match:
                return float(match.group(1))
    return None


def drm_extra(card_device):
    hw = _hwmon(card_device)
    temps = _temp_label_data(hw)
    hotspot = next((v for k, v in temps.items() if 'junction' in k or 'hotspot' in k or 'hot spot' in k), None)
    edge = next((v for k, v in temps.items() if 'edge' in k), None)
    if edge is None and temps:
        edge = next(iter(temps.values()))
    raw_pwm = num(read(os.path.join(hw, 'pwm1'))) if hw else None
    raw_max = num(read(os.path.join(hw, 'pwm1_max'))) if hw else None
    fan_percent = raw_pwm / raw_max * 100 if raw_pwm is not None and raw_max else None
    rpm = num(read(os.path.join(hw, 'fan1_input'))) if hw else None
    clk = _freq_active(os.path.join(card_device, 'pp_dpm_sclk'))
    memclk = _freq_active(os.path.join(card_device, 'pp_dpm_mclk'))
    uevent = read(os.path.join(card_device, 'uevent'))
    match = re.search(r'^DRIVER=(.+)$', uevent, re.M)
    return dict(hotspot=hotspot, edge=edge, fan_percent=fan_percent, fan_rpm=rpm,
                clock=clk, clock_mem=memclk, driver=match.group(1) if match else None)


def _default_route():
    for line in read('/proc/net/route').splitlines()[1:]:
        f = line.split()
        if len(f) < 4 or f[1] != '00000000':
            continue
        try:
            gateway = socket.inet_ntoa(struct.pack('<L', int(f[2], 16)))
            return f[0], gateway
        except (ValueError, OSError, struct.error):
            continue
    return None, None


def _dns():
    servers = []
    for line in read('/etc/resolv.conf').splitlines():
        m = re.match(r'^\s*nameserver\s+(\S+)', line)
        if m:
            servers.append(m.group(1))
    if servers == ['127.0.0.53'] or servers == ['127.0.0.54']:
        try:
            p = subprocess.run(['resolvectl','dns'], capture_output=True, text=True, timeout=1)
            extra = re.findall(r'(?<!\w)(?:\d{1,3}\.){3}\d{1,3}(?!\w)', p.stdout)
            extra = [x for x in extra if not x.startswith('127.')]
            if extra:
                servers = extra
        except (OSError, subprocess.TimeoutExpired):
            pass
    return list(dict.fromkeys(servers))


_route_cache = (0, {})

def net_static_details():
    global _route_cache
    now = time.monotonic()
    if now - _route_cache[0] >= 20:
        primary, gateway = _default_route()
        _route_cache = (now, {'route_interface': primary, 'gateway': gateway, 'dns': _dns()})
    return dict(_route_cache[1])


def sensor_info():
    try:
        temps = psutil.sensors_temperatures()
    except Exception:
        temps = {}
    try:
        fans = psutil.sensors_fans()
    except Exception:
        fans = {}
    out_temp, out_fans, volts, powers, frequencies = [], [], [], [], []
    for chip, entries in sorted(temps.items()):
        for idx, s in enumerate(entries):
            out_temp.append({'name': f'{chip} · {s.label or "Sensor " + str(idx + 1)}',
                             'value': s.current, 'high': s.high, 'critical': s.critical})
    for chip, entries in sorted(fans.items()):
        for idx, s in enumerate(entries):
            out_fans.append({'name': f'{chip} · {s.label or "Lüfter " + str(idx + 1)}',
                             'value': s.current})
    for hw in glob.glob('/sys/class/hwmon/hwmon*'):
        chip = read(os.path.join(hw, 'name')) or os.path.basename(hw)
        for file in glob.glob(os.path.join(hw, 'power*_average')) + glob.glob(os.path.join(hw, 'power*_input')):
            value = num(read(file), 1_000_000)
            if value is None or value < 0 or value > 5000:
                continue
            prefix = file.rsplit('_', 1)[0]
            caption = read(prefix + '_label') or os.path.basename(prefix)
            powers.append({'name': f'{chip} · {caption}', 'value': value})
        for file in glob.glob(os.path.join(hw, 'freq*_input')):
            value = num(read(file), 1_000_000)  # Linux hwmon frequency in Hz
            if value is None or value < 0 or value > 100000:
                continue
            prefix = file.rsplit('_', 1)[0]
            caption = read(prefix + '_label') or os.path.basename(prefix)
            frequencies.append({'name': f'{chip} · {caption}', 'value': value})
        for file in glob.glob(os.path.join(hw, 'in*_input')):
            v = num(read(file), 1000)
            if v is None or v < 0 or v > 30:
                continue
            prefix = file[:-6]
            label = read(prefix + '_label') or os.path.basename(prefix)
            volts.append({'name': f'{chip} · {label}', 'value': v})
    return {'temps': out_temp, 'fans': out_fans, 'voltages': volts, 'powers': powers, 'frequencies': frequencies}
