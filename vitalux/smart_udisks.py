"""Read-only UDisks2 SMART interface (ATA and NVMe).

Uses system busctl. No elevated privileges, destructive methods, or additional
Python modules. The result explicitly describes missing SMART interfaces.
"""
from __future__ import annotations
import json
import re
import shutil
import subprocess

DEST = 'org.freedesktop.UDisks2'
BLOCK = '/org/freedesktop/UDisks2/block_devices/'
DRIVE_PREFIX = '/org/freedesktop/UDisks2/drives/'


def _call(args, timeout=6):
    binary = shutil.which('busctl')
    if not binary:
        return None
    try:
        p = subprocess.run([binary, '--system', '--json=short', *args],
                           capture_output=True, text=True, timeout=timeout, check=False)
        if p.returncode != 0:
            return None
        return json.loads(p.stdout)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def _unpack(x):
    if isinstance(x, dict) and 'type' in x and 'data' in x:
        return _unpack(x['data'])
    if isinstance(x, list):
        return [_unpack(item) for item in x]
    if isinstance(x, dict):
        return {k: _unpack(v) for k, v in x.items()}
    return x


def _single(x):
    x = _unpack(x)
    while isinstance(x, list) and len(x) == 1:
        x = x[0]
    return x


def _props(path, iface, prop):
    return _single(_call(['get-property', DEST, path, iface, prop]))


def _value(loc, key):
    return _props(*loc, key)


def _dictionary(data):
    data = _single(data)
    if isinstance(data, dict):
        return data
    if not isinstance(data, list):
        return {}
    if all(isinstance(x, list) and len(x) == 2 for x in data):
        return {str(k): _single(v) for k, v in data}
    return {str(data[i]): _single(data[i + 1]) for i in range(0, len(data) - 1, 2)}


def _rows(data):
    data = _unpack(data)
    while isinstance(data, list) and len(data) == 1 and isinstance(data[0], list):
        if data[0] and isinstance(data[0][0], list):
            data = data[0]
        else:
            break
    return data if isinstance(data, list) else []


def _num(value):
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return None


def _base(name, drive):
    generic = (drive, 'org.freedesktop.UDisks2.Drive')
    return {'name': name, 'model': _value(generic, 'Model') or '–',
            'serial': _value(generic, 'Serial') or '–',
            'firmware': _value(generic, 'Revision') or '–',
            'capacity': _num(_value(generic, 'Size')), 'source': 'UDisks2',
            'health': 'Unbekannt', 'health_percent': None, 'temp': None,
            'attributes': []}


def _nvme(name, drive, base):
    api = 'org.freedesktop.UDisks2.NVMe.Controller'
    loc = (drive, api)
    # UDisks >= 2.10 provides this interface. Read SMART data; don't call
    # SmartUpdate in an unprivileged system-monitoring application.
    attrs = _dictionary(_call(['call', DEST, drive, api,
                               'SmartGetAttributes', 'a{sv}', '0']))
    updated = _num(_value(loc, 'SmartUpdated'))
    used = _num(attrs.get('percent_used'))
    if used is not None:
        base['health_percent'] = max(0, min(100, 100 - used))
        base['wear_used'] = used
    warnings = _value(loc, 'SmartCriticalWarning')
    if updated and updated > 0 and isinstance(warnings, list):
        # UDisks exposes a LIST of critical warnings, not an integer mask.
        # Missing warning data must not be interpreted as healthy.
        base['health'] = 'Warnung' if warnings else 'Gut'
    k = _num(_value(loc, 'SmartTemperature'))
    if k and k > 240:
        base['temp'] = round(k - 273.15)
    hours = _num(_value(loc, 'SmartPowerOnHours'))
    base['hours'] = hours
    base['standard'] = _value(loc, 'NVMeRevision') or '–'
    base['interface'] = 'NVMe'
    base['power_cycles'] = _num(attrs.get('power_cycles'))
    base['read_bytes'] = _num(attrs.get('total_data_read'))
    base['written_bytes'] = _num(attrs.get('total_data_written'))
    names = {'avail_spare': 'Verfügbare Reserve',
             'spare_thresh': 'Reserve-Schwelle',
             'percent_used': 'Verschleiß (genutzt)',
             'total_data_read': 'Gesamtdaten gelesen (Bytes)',
             'total_data_written': 'Gesamtdaten geschrieben (Bytes)',
             'ctrl_busy_time': 'Controller-Zeit (Min.)',
             'power_cycles': 'Einschaltvorgänge',
             'unsafe_shutdowns': 'Unsichere Abschaltungen',
             'media_errors': 'Medien-/Datenfehler',
             'num_err_log_entries': 'Fehlerprotokolleinträge'}
    for i, (key, value) in enumerate(attrs.items()):
        base['attributes'].append(dict(id=f'{i+1:02X}',
              name=names.get(key, key.replace('_', ' ').title()),
              current=None, worst=None, threshold=None,
              raw=str(value), failed=False))
    if not attrs and not (updated and updated > 0):
        base['error'] = ('UDisks2 liefert für dieses NVMe-Laufwerk keine SMART-Werte. '
                         'Möglicherweise fehlt die NVMe-SMART-Schnittstelle des Systemdienstes.')
    return base


def _ata(name, drive, base):
    api = 'org.freedesktop.UDisks2.Drive.Ata'
    loc = (drive, api)
    failed = _value(loc, 'SmartFailing')
    updated = _num(_value(loc, 'SmartUpdated'))
    if updated and updated > 0 and isinstance(failed, bool):
        base['health'] = 'Warnung' if failed else 'Gut'
    k = _num(_value(loc, 'SmartTemperature'))
    if k and k > 240:
        base['temp'] = round(k - 273.15)
    seconds = _num(_value(loc, 'SmartPowerOnSeconds'))
    base['hours'] = seconds // 3600 if seconds is not None else None
    base['interface'] = 'ATA/SATA'
    result = _call(['call', DEST, drive, api, 'SmartGetAttributes', 'a{sv}', '0'])
    # a(ysqiiixia{sv}): ID, name, flags, current, worst, threshold,
    # pretty-value, unit, unused-expansion. The pretty-value isn't necessarily
    # a raw vendor counter; don't pretend otherwise.
    rows = _rows(result)
    for row in rows:
        if not isinstance(row, list) or len(row) < 7:
            continue
        ident, attr_name, flags, current, worst, threshold, pretty = row[:7]
        unit = row[7] if len(row) > 7 else None
        units = {1: 'ms', 2: 'Sek.', 3: '°C', 4: 'Sektoren'}
        pretty_unit = units.get(unit, '')
        base['attributes'].append(dict(id=f'{ident:02X}' if isinstance(ident, int) else str(ident),
               name=str(attr_name), current=current, worst=worst,
               threshold=threshold, raw=f'{pretty} {pretty_unit}'.strip(), failed=False))
    if not base['attributes'] and base['health'] == 'Unbekannt':
        base['error'] = ('UDisks2 liefert keine ATA-SMART-Werte für dieses Laufwerk. '
                         'Möglicherweise fehlen Berechtigungen oder der Controller unterstützt den Zugriff nicht.')
    return base


def inspect_drive(name):
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', name or ''):
        return None
    drive = _props(BLOCK + name, 'org.freedesktop.UDisks2.Block', 'Drive')
    if not isinstance(drive, str) or not drive.startswith(DRIVE_PREFIX):
        return None
    base = _base(name, drive)
    if name.startswith('nvme'):
        return _nvme(name, drive, base)
    return _ata(name, drive, base)
