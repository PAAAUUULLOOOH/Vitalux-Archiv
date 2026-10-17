"""Non-destructive SMART telemetry. No guessed drive life or elevation."""
from __future__ import annotations
import json
import re
import shutil
import subprocess
from .bundled_tools import find_tool
from .smart_udisks import inspect_drive as inspect_with_udisks

NVME_FIELDS = [
 ('01','critical_warning','Kritische Warnung'),('02','temperature','Temperatur'),
 ('03','available_spare','Verfügbare Reserve'),('04','available_spare_threshold','Reserve-Schwelle'),
 ('05','percentage_used','Verschleiß (genutzt)'),('06','data_units_read','Dateneinheiten gelesen'),
 ('07','data_units_written','Dateneinheiten geschrieben'),('08','host_reads','Host-Lesevorgänge'),
 ('09','host_writes','Host-Schreibvorgänge'),('0A','controller_busy_time','Controller-Zeit (Min.)'),
 ('0B','power_cycles','Einschaltvorgänge'),('0C','power_on_hours','Betriebsstunden'),
 ('0D','unsafe_shutdowns','Unsichere Abschaltungen'),('0E','media_errors','Medien-/Datenfehler'),
 ('0F','num_err_log_entries','Fehlerprotokolleinträge'),
 ('10','warning_temp_time','Temperaturwarnungszeit'),('11','critical_comp_time','Kritische Temperaturzeit'),
]
LIFE_NAMES={'ssd_life_left','remaining_lifetime_perc','remaining_life','percent_lifetime_remain',
            'percent_lifetime_remaining','media_wearout_indicator','ssd_remaining_life','lifetime_left'}


def integer(x):
    try:return int(x)
    except (TypeError,ValueError,OverflowError):return None


def field(data,key):
    val=data.get(key)
    return str(val) if val not in (None,'') else '–'


def decode_smart(data):
    nvme=data.get('nvme_smart_health_information_log') or {}
    ata=(data.get('ata_smart_attributes') or {}).get('table') or []
    passed=(data.get('smart_status') or {}).get('passed')
    warning=integer(nvme.get('critical_warning'))
    used=integer(nvme.get('percentage_used'))
    remaining=max(0,min(100,100-used)) if used is not None else None
    if remaining is None:
        for x in ata:
            if str(x.get('name','')).lower() in LIFE_NAMES:
                candidate=integer(x.get('value'))
                if candidate is not None and 0<=candidate<=100:
                    remaining=candidate;break
    health=('Warnung' if passed is False or (warning is not None and warning!=0)
            else 'Gut' if passed is True or (bool(nvme) and warning==0)
            else 'Unbekannt')
    temperature=(data.get('temperature') or {}).get('current')
    if temperature is None:temperature=nvme.get('temperature')
    attributes=[]
    if nvme:
        for ident,key,title in NVME_FIELDS:
            value=nvme.get(key)
            if value is None:continue
            raw=str(value)+(' %' if key in ('available_spare','available_spare_threshold','percentage_used') else ' °C' if key=='temperature' else '')
            attributes.append(dict(id=ident,name=title,current=None,worst=None,threshold=None,raw=raw,failed=False))
    else:
        for x in ata:
            raw=x.get('raw') or {}
            ident=integer(x.get('id'))
            attributes.append(dict(id=f'{ident:02X}' if ident is not None else '–',name=field(x,'name'),
                                   current=x.get('value'),worst=x.get('worst'),threshold=x.get('thresh'),
                                   raw=raw.get('string') or str(raw.get('value','–')),
                                   failed=x.get('when_failed') not in ('never',None,'','-')))
    capacity=(data.get('user_capacity') or {}).get('bytes')
    speeds=data.get('interface_speed') or {}
    current=speeds.get('current') or {}
    maximum=speeds.get('max') or {}
    if isinstance(current,dict):current=current.get('string')
    if isinstance(maximum,dict):maximum=maximum.get('string')
    transfer=(str(current or '–') + (' | '+str(maximum) if maximum else '')) if speeds else 'PCIe / NVMe' if nvme else (data.get('sata_version') or {}).get('string') or '–'
    read=integer(nvme.get('data_units_read'))
    written=integer(nvme.get('data_units_written'))
    return {
        'health':health,'health_percent':remaining,'wear_used':used,'temp':integer(temperature),
        'hours':integer((data.get('power_on_time') or {}).get('hours') or nvme.get('power_on_hours')),
        'power_cycles':integer(data.get('power_cycle_count') or nvme.get('power_cycles')),
        'read_bytes':read*512000 if read is not None else None,
        'written_bytes':written*512000 if written is not None else None,
        'model':data.get('model_name') or data.get('model_family') or data.get('product') or '–',
        'serial':field(data,'serial_number'),'firmware':field(data,'firmware_version'),
        'capacity':integer(capacity),'interface':(data.get('device') or {}).get('protocol') or ('NVMe' if nvme else 'ATA'),
        'transfer_mode':transfer,
        'standard':(data.get('nvme_version') or {}).get('string','–') if nvme else (data.get('ata_version') or {}).get('string','–'),
        'rotation_rate':integer(data.get('rotation_rate')),'form_factor':(data.get('form_factor') or {}).get('name','–'),
        'attributes':attributes,'source':'smartctl',
    }


def fallback_basic(name,timeout=6):
    tool=shutil.which('udisksctl')
    if not tool:return None
    try:
        response=subprocess.run([tool,'info','-b','/dev/'+name],capture_output=True,text=True,timeout=timeout)
        if response.returncode:return None
        lines=dict(x.strip() for x in (line.split(':',1) for line in response.stdout.splitlines() if ':' in line))
    except (OSError,subprocess.TimeoutExpired,ValueError):return None
    return {'name':name,'model':lines.get('Model','–'),'serial':lines.get('Serial','–'),
            'firmware':lines.get('Revision','–'),'source':'UDisks2 (Basisdaten)',
            'health':'Unbekannt','health_percent':None,'attributes':[],
            'error':'Keine vollständigen SMART-Daten verfügbar (SMART-Zugriff/Controller prüfen).'}


def inspect_drive(name, timeout=8):
    """Return SMART data if available, otherwise a *specific* diagnostic.

    UDisks2 uses the system's privileged daemon for supported controllers;
    it requires neither smartctl nor a password in the typical case.
    """
    if not isinstance(name, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', name):
        return {'name': name, 'error': 'Ungültiger Gerätename'}
    smartctl = find_tool('smartctl')
    if smartctl:
        try:
            p = subprocess.run([smartctl, '-a', '-j', '/dev/' + name],
                               capture_output=True, text=True, timeout=timeout,
                               check=False)
            data = json.loads(p.stdout)
            if any(x in data for x in ('smart_status', 'nvme_smart_health_information_log',
                                      'ata_smart_attributes', 'temperature')):
                return {'name': name, **decode_smart(data)}
            messages = [x.get('string', '') for x in (data.get('smartctl') or {}).get('messages', [])
                        if isinstance(x, dict)]
            detail = ' '.join(x for x in messages if x).strip()
            smart_error = ('smartctl: ' + detail[:220]) if detail else (
                'smartctl konnte keine SMART-Daten auslesen (Gerätezugriff oder Controller).')
        except (OSError, ValueError, subprocess.TimeoutExpired):
            smart_error = 'smartctl konnte keine lesbaren SMART-Daten liefern.'
    else:
        smart_error = ('smartctl ist nicht gebündelt oder installiert. '
                       'Der alternative Zugriff über UDisks2 liefert keine vollständigen SMART-Werte.')
    udisks = inspect_with_udisks(name)
    if udisks and not udisks.get('error'):
        return udisks
    if udisks:
        # Preserve genuine base device information, but explain the actual gap.
        udisks['error'] = udisks.get('error') or smart_error
        return udisks
    fallback = fallback_basic(name, timeout)
    if fallback:
        fallback['error'] = smart_error
        return fallback
    return {'name': name, 'error': smart_error}


def scan(drives):
    return [inspect_drive(d['name']) for d in drives if d.get('name')]
