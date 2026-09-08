"""Control only the dedicated player using Omarchy's native Hyprland dispatchers."""
import json
import subprocess
import time

def query(name):
    return json.loads(subprocess.check_output(['hyprctl', '-j', name], text=True, timeout=3))

def client(pid):
    return next((c for c in query('clients') if c.get('pid') == pid), None)

def dispatch(method, address, **options):
    options['window'] = 'address:' + address
    fields = ', '.join(key + ' = ' + json.dumps(value) for key, value in options.items())
    result = subprocess.run(['hyprctl', 'dispatch', f'hl.dsp.window.{method}({{ {fields} }})'],
                            capture_output=True, text=True, timeout=3)
    if result.returncode or result.stdout.strip() != 'ok':
        raise RuntimeError('Window control failed: ' + (result.stdout or result.stderr).strip())

def geometry(monitor, width, corner, aspect=4/3):
    scale = monitor.get('scale', 1)
    mw, mh = monitor['width'], monitor['height']
    if monitor.get('transform', 0) % 2: mw, mh = mh, mw
    mw, mh = int(mw / scale), int(mh / scale)
    left, top, right, bottom = monitor.get('reserved', [0, 0, 0, 0])
    aw, ah = max(1, mw-left-right-32), max(1, mh-top-bottom-32)
    width = max(1, int(min(width, aw, ah*aspect)))
    height = max(1, int(width/aspect))
    x = monitor['x'] + (left+16 if corner.endswith('left') else mw-right-width-16)
    y = monitor['y'] + (top+16 if corner.startswith('top') else mh-bottom-height-16)
    return width, height, x, y

def apply(pid, mode, prefs):
    win = None
    for _ in range(40):
        win = client(pid)
        if win: break
        time.sleep(.05)
    if not win: raise RuntimeError('Player window is not available yet')
    addr = win['address']
    dispatch('fullscreen', addr, mode='fullscreen', action='unset')
    if win.get('pinned'): dispatch('pin', addr)
    if mode == 'tiled':
        dispatch('float', addr, action='off')
        return
    dispatch('float', addr, action='on')
    monitor = next(m for m in query('monitors') if m['id'] == win['monitor'])
    width = prefs.get('miniWidth', 320) if mode == 'mini' else 960
    w, h, x, y = geometry(monitor, width, prefs.get('corner', 'bottom-right'))
    dispatch('resize', addr, x=w, y=h)
    if mode == 'mini':
        dispatch('move', addr, x=x, y=y)
        dispatch('pin', addr)
        dispatch('alter_zorder', addr, mode='top')
    else:
        dispatch('center', addr)
        if mode == 'fullscreen': dispatch('fullscreen', addr, mode='fullscreen', action='set')
