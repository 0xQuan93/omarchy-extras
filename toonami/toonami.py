#!/usr/bin/env python3
"""Public Toonami guide and a dedicated, serialized MPV television session."""
import argparse
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import time
import urllib.parse
import urllib.request
import windowing

BASE = Path(__file__).resolve().parent
RUNTIME = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}'))
SOCKET = RUNTIME / 'quan-toonami.sock'
STATE = RUNTIME / 'quan-toonami.json'
STATIONS = [
    dict(key='east', name='Toonami Aftermath East', stream='est', number=19),
    dict(key='west', name='Toonami Aftermath West', stream='est', number=20, delay=180),
    dict(key='snick-east', name='Snickelodeon East', number=21, gated=True),
    dict(key='snick-west', name='Snickelodeon West', number=22, gated=True),
    dict(key='mtv', name='MTV97', number=23, gated=True),
    dict(key='movies', name='Movies', stream='movies', number=24),
    dict(key='radio', name='Toonami Aftermath Radio', stream='radio', number=25),
]

def saved_state():
    try: return json.loads(STATE.read_text())
    except (OSError, ValueError): return {}

def save_state(**values):
    data = saved_state()
    data.update(values)
    STATE.write_text(json.dumps(data))

def set_mode(mode):
    windowing.apply(ipc('get_property', 'pid'), mode, saved_state())
    save_state(mode=mode)

def fetch(path):
    context = ssl.create_default_context()
    # Supply missing server intermediates; certificate/hostname verification stays on.
    context.load_verify_locations(str(BASE / 'issuer-chain.pem'))
    request = urllib.request.Request('https://api.toonamiaftermath.com/' + path,
                                    headers={'User-Agent': 'QuanToonami/1.0', 'Referer': 'https://www.toonamiaftermath.com/'})
    with urllib.request.urlopen(request, timeout=18, context=context) as response:
        return response.read(2_000_000).decode()

def ipc(*args):
    with socket.socket(socket.AF_UNIX) as conn:
        conn.settimeout(3)
        conn.connect(str(SOCKET))
        conn.sendall((json.dumps({'command': list(args), 'request_id': 1}) + '\n').encode())
        with conn.makefile('r') as lines:
            for line in lines:
                data = json.loads(line)
                if data.get('request_id') == 1:
                    if data.get('error') != 'success':
                        raise RuntimeError(data.get('error', 'Player error'))
                    return data.get('data')
    raise RuntimeError('Player disconnected')

def status():
    try:
        selected = json.loads(STATE.read_text()).get('selected', 'east')
    except (OSError, ValueError):
        selected = 'east'
    prefs = saved_state()
    result = dict(selected=selected, playing=False, paused=False, fullscreen=False,
                  mode=prefs.get('mode', 'window'), miniWidth=prefs.get('miniWidth', 320),
                  corner=prefs.get('corner', 'bottom-right'))
    try:
        result.update(playing=not ipc('get_property', 'idle-active'),
                      paused=ipc('get_property', 'pause'), fullscreen=ipc('get_property', 'fullscreen'))
        win = windowing.client(ipc('get_property', 'pid'))
        if win:
            result['mode'] = ('fullscreen' if win.get('fullscreen') else
                              'mini' if win.get('pinned') else
                              'window' if win.get('floating') else 'tiled')
            result['fullscreen'] = bool(win.get('fullscreen'))
    except (OSError, RuntimeError):
        pass
    return result

def guide_rows(data, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    rows = []
    for station in STATIONS:
        row = dict(station, now='Account access · open official site' if station.get('gated') else 'Schedule unavailable', next='')
        media = next((c.get('media', []) for c in data if c.get('name') == station['name']), [])
        dated = []
        for item in media:
            try:
                dated.append((dt.datetime.fromisoformat(item['startDate'].replace('Z', '+00:00')), item))
            except (KeyError, ValueError, TypeError):
                continue
        dated.sort(key=lambda pair: pair[0])
        current = [pair for pair in dated if pair[0] <= now]
        future = [pair for pair in dated if pair[0] > now]
        if current and not station.get('gated'):
            item = current[-1][1]
            info = item.get('info') or {}
            row['now'] = info.get('fullname') or item.get('name', 'Live')
            if info.get('episode'):
                row['now'] += ' · ' + info['episode']
        if future and not station.get('gated'):
            start, item = future[0]
            row['next'] = start.astimezone().strftime('%I:%M %p').lstrip('0') + ' · ' + item.get('name', 'Up next')
        rows.append(row)
    return rows

def guide():
    cache = RUNTIME / 'quan-toonami-guide.json'
    error = ''
    try:
        data = json.loads(fetch('channelsCurrentMedia'))
        if not isinstance(data, list):
            raise ValueError('Unexpected guide response')
        cache.write_text(json.dumps(data))
    except Exception:
        error = 'Guide offline · showing saved schedule'
        try:
            data = json.loads(cache.read_text())
        except (OSError, ValueError):
            data = []
            error = 'Guide unavailable · channels still selectable'
    return dict(stations=guide_rows(data), error=error)

def stream_url(station):
    offset = -dt.datetime.now().astimezone().utcoffset().total_seconds() / 3600
    params = dict(channelName=station['stream'], timezoneOffset=offset, useHttps='true')
    if station.get('delay'):
        params['streamDelay'] = station['delay']
    url = fetch('streamUrl?' + urllib.parse.urlencode(params)).strip().strip('"')
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != 'https' or not parsed.hostname or not parsed.hostname.endswith('.toonamiaftermath.com') or '.m3u8' not in parsed.path:
        raise RuntimeError('Stream unavailable; try the official site')
    return url

def start_player():
    ca = RUNTIME / 'quan-toonami-ca.pem'
    ca.write_text(Path('/etc/ssl/certs/ca-certificates.crt').read_text() + (BASE / 'issuer-chain.pem').read_text())
    with (RUNTIME / 'quan-toonami-mpv.log').open('w') as log:
        process = subprocess.Popen([
            '/usr/bin/mpv', '--no-config', '--no-terminal', '--idle=yes', '--force-window=yes',
            '--pause=yes', '--volume=40', '--title=Toonami Aftermath', '--autofit=960x720',
            '--keepaspect-window=yes', '--input-ipc-server=' + str(SOCKET),
            '--tls-verify=yes', '--tls-ca-file=' + str(ca),
            '--referrer=https://www.toonamiaftermath.com/',
            '--input-conf=' + str(BASE / 'input.conf'),
        ], stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
    for _ in range(80):
        if process.poll() is not None:
            raise RuntimeError('Player failed to start')
        try:
            ipc('get_property', 'idle-active')
            return
        except OSError:
            time.sleep(.05)
    raise RuntimeError('Player did not become ready')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['guide', 'status', 'play', 'fullscreen', 'toggle', 'stop', 'site', 'next', 'previous', 'mini', 'window', 'tiled', 'smaller', 'larger', 'corner'])
    parser.add_argument('station', nargs='?', choices=[s['key'] for s in STATIONS])
    parser.add_argument('--paused', action='store_true')
    args = parser.parse_args()
    if args.action == 'guide':
        return guide()
    if args.action == 'status':
        return status()
    with (RUNTIME / 'quan-toonami.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = status()
        modes = {'mini', 'window', 'tiled', 'fullscreen'}
        if args.action in {'smaller', 'larger', 'corner'}:
            if args.action == 'corner':
                corners = ['bottom-right', 'bottom-left', 'top-left', 'top-right']
                save_state(corner=corners[(corners.index(state['corner']) + 1) % 4])
            else:
                save_state(miniWidth=max(240, min(640, state['miniWidth'] + (80 if args.action == 'larger' else -80))))
            if state['playing']: set_mode('mini')
            return status()
        if args.action in modes and state['playing']:
            set_mode('window' if args.action == 'fullscreen' and state['fullscreen'] else args.action)
            return status()
        key = args.station or state['selected']
        if args.action in ('next', 'previous'):
            keys = [s['key'] for s in STATIONS if not s.get('gated')]
            index = keys.index(key) if key in keys else 0
            key = keys[(index + (1 if args.action == 'next' else -1)) % len(keys)]
        station = next(s for s in STATIONS if s['key'] == key)
        if args.action == 'site' or (station.get('gated') and args.action in ({'play'} | modes)):
            subprocess.Popen(['xdg-open', 'https://www.toonamiaftermath.com/?' + urllib.parse.urlencode({'channelName': station['name']})], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif args.action == 'stop':
            if SOCKET.exists():
                try: ipc('quit')
                except OSError: pass
        elif args.action == 'toggle':
            if state['playing']: ipc('cycle', 'pause')
        else:
            url = stream_url(station)
            created = False
            try: ipc('get_property', 'idle-active')
            except (OSError, RuntimeError):
                start_player()
                created = True
            ipc('set_property', 'pause', True)
            ipc('loadfile', url, 'replace')
            save_state(selected=key)
            ipc('set_property', 'force-media-title', station['name'])
            if args.action in modes: set_mode(args.action)
            elif created: set_mode(state['mode'])
            ipc('set_property', 'pause', args.paused)
        return status()

if __name__ == '__main__':
    try:
        print(json.dumps(main()))
    except Exception as error:
        print(json.dumps({'error': str(error)}))
        raise SystemExit(1)
