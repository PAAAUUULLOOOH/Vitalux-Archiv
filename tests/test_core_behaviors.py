"""Alert and settings regression checks."""
import os
import sys
sys.path.insert(0, os.getcwd())
import json
import tempfile
from pathlib import Path
from vitalux import alerts, settings

def test_alerts():
    sample = {'cpu': {'temp': 70}, 'gpus': [{'temp': 55}, {'temp': 96}],
              'ram': {'percent': 30}, 'disks': [{'mount': '/', 'percent': 40}]}
    a = alerts.readings_from_sample(sample)
    assert a['gpu_temp'][0] == 96
    monitor = alerts.AlertMonitor()
    assert len(monitor.update(a, {'gpu_temp': 90}, True)) == 1
    assert not monitor.update(a, {'gpu_temp': 90}, True)
    a['gpu_temp'] = (85, '°C')
    monitor.update(a, {'gpu_temp': 90}, True)
    a['gpu_temp'] = (91, '°C')
    assert len(monitor.update(a, {'gpu_temp': 90}, True)) == 1
    a['gpu_temp'] = (float('nan'), '°C')
    assert not monitor.update(a, {'gpu_temp': 90}, True)

def test_settings():
    original = settings.PATH
    try:
        with tempfile.TemporaryDirectory() as folder:
            settings.PATH = os.path.join(folder, 'prefs', 'settings.json')
            assert settings.set('threshold', 90)
            assert settings.get('threshold') == 90
            assert json.loads(Path(settings.PATH).read_text())['threshold'] == 90
            assert not list(Path(settings.PATH).parent.glob('.settings-*'))
            Path(settings.PATH).write_text('{"threshold": 88}')
            assert settings.get('threshold') == 88
            assert settings.set_many({'cpu_temp': 88, 'gpu_temp': 95})
            stat_before = Path(settings.PATH).stat()
            assert settings.get_many({'cpu_temp': 90, 'gpu_temp': 90,
                                      'ram_usage': 93}) == {
                'cpu_temp': 88, 'gpu_temp': 95, 'ram_usage': 93}
            assert settings.set_many({'cpu_temp': 88, 'gpu_temp': 95})
            assert Path(settings.PATH).stat().st_ino == stat_before.st_ino, (
                'An unchanged preference should not rewrite the file')
            assert settings.get('threshold') == 88, (
                'Batch updates must preserve unrelated user settings')
            replacement = {'colors': [{'color': '#123456'}]}
            assert settings.set_many(replacement)
            replacement['colors'].append({'color': '#ffffff'})
            assert settings.get('colors') == [{'color': '#123456'}], (
                'Changes to caller data must not mutate the cached settings')
    finally:
        settings.PATH = original

if __name__ == '__main__':
    test_alerts()
    test_settings()
    print('Core alerts and settings regressions: PASS')
