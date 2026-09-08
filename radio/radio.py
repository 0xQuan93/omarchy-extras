#!/usr/bin/env python3
"""Control a dedicated MPV radio instance without disturbing other players."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import socket
import subprocess
import time

STATIONS = {
    'groovesalad': 'https://somafm.com/groovesalad.pls',
    'dronezone': 'https://somafm.com/dronezone.pls',
    'deepspaceone': 'https://somafm.com/deepspaceone.pls',
}
runtime = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}'))
socket_path = runtime / 'quan-radio.sock'


def command(*args):
    with socket.socket(socket.AF_UNIX) as connection:
        connection.settimeout(3)
        connection.connect(str(socket_path))
        connection.sendall((json.dumps({'command': list(args), 'request_id': 89}) + '\n').encode())
        with connection.makefile('r') as response:
            for line in response:
                result = json.loads(line)
                if result.get('request_id') == 89:
                    if result.get('error') != 'success':
                        raise RuntimeError(result.get('error', 'Radio command failed'))
                    return result.get('data')
        raise RuntimeError('Radio disconnected')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=[*STATIONS, 'stop', 'toggle', 'status'])
    parser.add_argument('--paused', action='store_true', help='Load without playing')
    args = parser.parse_args()
    with (runtime / 'quan-radio.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            command('get_property', 'idle-active')
        except (OSError, RuntimeError):
            if args.action not in STATIONS:
                print('Radio is off')
                return
            process = subprocess.Popen([
                '/usr/bin/mpv', '--no-config', '--no-terminal', '--idle=yes', '--no-video',
                '--audio-display=no', '--volume=40', '--pause=yes', '--title=Quan Radio',
                '--script=/usr/lib/mpv-mpris/mpris.so', f'--input-ipc-server={socket_path}',
            ], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
               stderr=subprocess.DEVNULL, start_new_session=True)
            for _ in range(60):
                if process.poll() is not None:
                    raise RuntimeError('MPV could not start')
                try:
                    command('get_property', 'idle-active')
                    break
                except OSError:
                    time.sleep(.05)
            else:
                raise RuntimeError('Radio did not become ready')
        if args.action == 'stop':
            command('stop')
        elif args.action == 'toggle':
            command('cycle', 'pause')
        elif args.action == 'status':
            print(json.dumps({'paused': command('get_property', 'pause'),
                              'idle': command('get_property', 'idle-active'),
                              'title': command('get_property', 'media-title')}))
        else:
            command('set_property', 'pause', True)
            command('loadfile', STATIONS[args.action], 'replace')
            command('set_property', 'pause', args.paused)


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, ValueError) as error:
        subprocess.run(['/usr/bin/notify-send', 'Quan Radio', str(error)], check=False)
        raise SystemExit(str(error))
