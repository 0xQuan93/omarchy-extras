#!/usr/bin/env python3
"""Install selected extras. Without --apply, print the plan without writing."""
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
COMPONENTS = {
    'dashboard': ('dashboard', 'home', 'left', 'quan-dashboard'),
    'wanderer': ('dashboard/wanderer', 'wanderer', None, None),
    'weather': ('weather', 'weather', 'right', None),
    'radio': ('radio', 'media', 'left', None),
    'toonami': ('toonami', 'toonami', 'left', None),
    'wavewarz': ('wavewarz', 'wavewarz', 'right', 'quan-wavewarz'),
    'notifications': ('notifications', 'notifications', None, None),
    'theme': ('themes/regalia-89', None, None, None),
}


def selection(names):
    chosen = set(COMPONENTS) if 'all' in names else set(names)
    if chosen & {'weather', 'wanderer'}:
        chosen.add('dashboard')
    return [name for name in COMPONENTS if name in chosen]


def configure(data, names, config):
    """Merge our entries; preserve unrelated user settings and widget options."""
    layout = data['bar']['layout']
    for name in names:
        _, ident, section, _ = COMPONENTS[name]
        if not ident:
            continue
        pid = 'oxquan.' + ident
        disabled = data.setdefault('disabledPlugins', [])
        if pid in disabled:
            disabled.remove(pid)
        if section:
            existing = next((entry for entries in layout.values() for entry in entries if entry.get('id') == pid), None)
            if existing is None:
                entry = {'id': pid}
                if name in ('radio', 'toonami'):
                    entry.update(type='qml', source=str(config/'plugins'/pid/'BarWidget.qml'))
                layout.setdefault(section, []).append(entry)
        if not section or name == 'wavewarz':
            plugins = data.setdefault('plugins', [])
            if not any(p.get('id') == pid for p in plugins):
                plugins.append({'id': pid})
        if name == 'notifications' and 'omarchy.notifications' not in disabled:
            disabled.append('omarchy.notifications')
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('components', nargs='+', choices=[*COMPONENTS, 'all'])
    parser.add_argument('--apply', action='store_true', help='write files and start selected user services')
    parser.add_argument('--no-start', action='store_true', help='write service files without starting services')
    args = parser.parse_args()
    names = selection(args.components)
    home = Path.home()
    config = Path(os.environ.get('XDG_CONFIG_HOME', home/'.config'))/'omarchy'
    data_dir = Path(os.environ.get('XDG_DATA_HOME', home/'.local/share'))/'omarchy-extras'
    state = Path(os.environ.get('XDG_STATE_HOME', home/'.local/state'))/'omarchy-extras'
    if not all(p.is_absolute() for p in (config, data_dir, state)):
        parser.error('XDG directories must be absolute paths.')
    shell = config/'shell.json'
    try:
        original = shell.read_text()
        data = json.loads(original)
        layout = data['bar']['layout']
        if not isinstance(layout, dict) or not all(isinstance(v, list) and all(isinstance(e, dict) for e in v) for v in layout.values()):
            raise ValueError('Expected bar.layout sections containing widget objects')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(f'Expected an existing Omarchy Quickshell shell.json at {shell}: {exc}')
    requirements = {'dashboard': ['python3', 'systemctl'], 'wanderer': ['chromium', 'hyprctl'],
                    'radio': ['mpv'], 'toonami': ['mpv', 'hyprctl'], 'wavewarz': ['curl', 'systemctl']}
    missing = sorted({cmd for name in names for cmd in requirements.get(name, []) if not shutil.which(cmd)})
    if 'radio' in names and not Path('/usr/lib/mpv-mpris/mpris.so').is_file():
        missing.append('/usr/lib/mpv-mpris/mpris.so (mpv-mpris)')
    print('Components: ' + ', '.join(names))
    print(f'Helpers: {data_dir}\nPlugins/theme: {config}\nBackups: {state}/backups')
    print('Services: ' + ', '.join(COMPONENTS[n][3] for n in names if COMPONENTS[n][3]))
    if 'notifications' in names:
        print('Notifications: disables the stock notification plugin while the custom service is active.')
    print('Theme is copied only. Apply it explicitly with: omarchy theme set regalia-89')
    if missing:
        print('Missing dependencies: ' + ', '.join(missing))
    if not args.apply:
        print('Preview only. Add --apply to install.')
        return
    if missing:
        parser.error('Install missing dependencies before applying.')
    # Concurrent settings edits should never be replaced with an older snapshot.
    if shell.read_text() != original:
        parser.error('shell.json changed during planning; rerun the installer.')
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup = state/'backups'/stamp
    records = []

    def write(path, content, preserve=False):
        if path.is_symlink():
            raise RuntimeError(f'Refusing to overwrite symlink: {path}')
        if path.exists():
            if preserve or path.read_bytes() == content:
                return
            saved = backup/str(len(records))
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, saved)
            records.append({'path': str(path), 'backup': str(saved)})
        else:
            records.append({'path': str(path), 'backup': None})
        backup.mkdir(parents=True, exist_ok=True)
        (backup/'manifest.json').write_text(json.dumps(records, indent=2)+'\n')
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name+'.omarchy-extras-tmp')
        # Exclusive creation avoids following an existing temporary symlink.
        with tmp.open('xb') as handle:
            handle.write(content)
        tmp.replace(path)

    # QML placeholders occur only inside double-quoted string literals.
    escaped_data = json.dumps(str(data_dir))[1:-1]
    for name in names:
        relative, ident, _, service = COMPONENTS[name]
        source = ROOT/relative
        for file in source.rglob('*'):
            if not file.is_file() or '__pycache__' in file.parts or file.name.startswith('test_') or file.suffix == '.md':
                continue
            rel = file.relative_to(source)
            # Dashboard's nested Wanderer files are needed by its web routes.
            # The desktop plugin is activated only when Wanderer is selected.
            if 'plugin' in rel.parts:
                continue
            if name == 'theme':
                target = config/'themes/regalia-89'/rel
            else:
                target = data_dir/relative/rel
            content = file.read_bytes()
            if file.name == 'input.conf':
                content = file.read_text().replace('@DATA@', escaped_data).encode()
            write(target, content, preserve=file.name in ('settings.json', 'readings.json'))
        if ident:
            for file in (source/'plugin').rglob('*'):
                if file.is_file():
                    content = file.read_bytes()
                    if file.suffix == '.qml':
                        content = file.read_text().replace('@DATA@', escaped_data).encode()
                    write(config/'plugins'/('oxquan.'+ident)/file.relative_to(source/'plugin'), content)
        if service:
            # systemd quoted values use C-style escapes and percent specifiers.
            folder = str(data_dir/relative).replace('%', '%%')
            unit = ('[Unit]\nDescription=Omarchy Extras '+name+'\nAfter=graphical-session.target\nPartOf=graphical-session.target\n'
                    '[Service]\nType=simple\n'
                    'ExecStart=/usr/bin/python3 '+json.dumps(folder+'/server.py')+'\nRestart=on-failure\nRestartSec=3\n'
                    '[Install]\nWantedBy=graphical-session.target\n')
            write(config.parent/'systemd/user'/f'{service}.service', unit.encode())
    new = json.dumps(configure(data, names, config), indent=2)+'\n'
    if shell.read_text() != original:
        raise RuntimeError('shell.json changed while copying files; settings were left untouched. Rerun.')
    write(shell, new.encode())
    services = [COMPONENTS[n][3]+'.service' for n in names if COMPONENTS[n][3]]
    if services and not args.no_start:
        subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
        subprocess.run(['systemctl', '--user', 'enable', '--now', *services], check=True)
        subprocess.run(['systemctl', '--user', 'restart', *services], check=True)
    print(f'Installed. Backup manifest: {backup}/manifest.json')


if __name__ == '__main__':
    main()
