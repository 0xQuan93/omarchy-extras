import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('installer', ROOT/'install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def test_merge_preserves_settings_and_is_idempotent(self):
        original = {'idle': {'lock': 600}, 'bar': {'layout': {'left': [{'id':'omarchy.menu'}], 'right': []}}}
        result = installer.configure(original, ['toonami', 'notifications', 'wavewarz'], Path('/tmp/config'))
        first = json.dumps(result, sort_keys=True)
        self.assertEqual(result['idle'], {'lock':600})
        self.assertEqual(result['bar']['layout']['left'][0], {'id':'omarchy.menu'})
        installer.configure(result, ['toonami', 'notifications', 'wavewarz'], Path('/tmp/config'))
        self.assertEqual(json.dumps(result, sort_keys=True), first)
        self.assertIn('omarchy.notifications', result['disabledPlugins'])

    def test_preview_install_backup_and_preserved_readings(self):
        with tempfile.TemporaryDirectory(prefix='extras test ') as temp:
            home = Path(temp)
            config = home/'config/omarchy'
            config.mkdir(parents=True)
            shell = config/'shell.json'
            original = json.dumps({'idle': {'lock': 601}, 'bar': {'layout': {'left': [], 'right': []}}})
            shell.write_text(original)
            env = dict(os.environ, HOME=temp, XDG_CONFIG_HOME=str(home/'config'),
                       XDG_DATA_HOME=str(home/'data'), XDG_STATE_HOME=str(home/'state'))
            command = [sys.executable, str(ROOT/'install.py'), 'dashboard', 'theme', '--no-start']
            subprocess.run(command, env=env, check=True, capture_output=True)
            self.assertFalse((home/'data').exists())
            self.assertEqual(shell.read_text(), original)
            subprocess.run(command+['--apply'], env=env, check=True, capture_output=True)
            installed = home/'data/omarchy-extras'
            readings = installed/'dashboard/wanderer/readings.json'
            readings.write_text('[{"title":"My private reading"}]')
            subprocess.run(command+['--apply'], env=env, check=True, capture_output=True)
            self.assertIn('My private reading', readings.read_text())
            self.assertEqual(json.loads(shell.read_text())['idle']['lock'],601)
            self.assertEqual(len(json.loads(shell.read_text())['bar']['layout']['left']),1)
            manifests = list((home/'state/omarchy-extras/backups').glob('*/manifest.json'))
            saved = [row for f in manifests for row in json.loads(f.read_text()) if row['path']==str(shell) and row['backup']]
            self.assertTrue(any(Path(r['backup']).read_text()==original for r in saved))
            unit=(home/'config/systemd/user/quan-dashboard.service').read_text()
            self.assertIn('"'+str(installed/'dashboard/server.py')+'"',unit)
            self.assertFalse((home/'config/hypr').exists())

    def test_dependencies(self):
        self.assertEqual(installer.selection(['weather']), ['dashboard', 'weather'])
        self.assertIn('dashboard',installer.selection(['wanderer']))

if __name__ == '__main__':
    unittest.main()
