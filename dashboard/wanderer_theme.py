"""Read the active palette through Omarchy's own alias and light-mode resolver."""
from pathlib import Path
import re
import subprocess
import threading

THEME = Path.home() / '.local/state/omarchy/current/theme'
_lock = threading.Lock()
_signature = None
_css = b''


def render(palette):
    def color(key, fallback):
        value = palette.get(key, '')
        return value if re.fullmatch(r'#[0-9a-fA-F]{6}', value) else fallback

    bg = color('background', '#101315')
    fg = color('foreground', '#cacccc')
    accent = color('accent', color('blue', fg))
    mode = 'light' if palette.get('mode') == 'light' else 'dark'
    return (':root{' + ';'.join([
        f'color-scheme:{mode}', f'--background:{bg}', f'--foreground:{fg}',
        f'--accent:{accent}',
        f'--surface:color-mix(in srgb,{bg} 94%,{fg})',
        f'--muted:color-mix(in srgb,{fg} 78%,{bg})',
        f'--border:color-mix(in srgb,{fg} 22%,{bg})',
        f'--accent-border:color-mix(in srgb,{accent} 40%,{bg})',
        f'--hover:color-mix(in srgb,{accent} 16%,{bg})',
        f'--selection:{color("selection_background", accent)}',
        f'--selection-foreground:{color("selection_foreground", fg)}',
    ]) + '}\n').encode()


def stylesheet():
    global _signature, _css
    with _lock:
        try:
            signature = ((THEME / 'colors.toml').read_bytes(), (THEME / 'light.mode').exists())
            if signature != _signature:
                output = subprocess.check_output(
                    ['omarchy', 'theme', 'color', '--file', str(THEME / 'colors.toml'), '--all'],
                    text=True, timeout=5)
                palette = dict(line.split('\t', 1) for line in output.splitlines() if '\t' in line)
                if not all(re.fullmatch(r'#[0-9a-fA-F]{6}', palette.get(k, '')) for k in ('background', 'foreground')):
                    raise ValueError('Theme palette is incomplete')
                _css = render(palette)
                _signature = signature
        except (OSError, ValueError, subprocess.SubprocessError):
            # A theme switch may briefly replace the directory. Keep the last good palette.
            pass
        return _css or render({})
