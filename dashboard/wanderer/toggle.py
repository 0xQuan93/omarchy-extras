#!/usr/bin/env python3
"""Show or hide the reading room without disturbing the active workspace."""
import json
import subprocess
import sys
import time

def ctl(*args):
    result = subprocess.run(['hyprctl', *args], text=True, capture_output=True, timeout=10)
    if result.returncode:
        raise RuntimeError(result.stdout.strip() or result.stderr.strip() or 'Hyprland command failed')
    return result.stdout

def window():
    return next((c for c in json.loads(ctl('clients', '-j')) if c.get('title') == "Wanderer's Desk" or c.get('initialTitle') == "Wanderer's Desk"), None)

preload = '--preload' in sys.argv
c = window()
if not c:
    ctl('eval', 'hl.exec_cmd("chromium --app=http://127.0.0.1:8990/wanderer/ --class=quan-wanderer", { workspace = "special:wanderer silent" })')
    for _ in range(40):
        time.sleep(.2)
        c = window()
        if c:
            break
if c:
    if c.get('workspace', {}).get('name') != 'special:wanderer':
        target = json.dumps('address:' + c['address'])
        ctl('dispatch', 'hl.dsp.window.move({ workspace = "special:wanderer", window = ' + target + ', follow = false })')
    if not preload:
        ctl('dispatch', 'hl.dsp.workspace.toggle_special("wanderer")')
else:
    raise RuntimeError("Wanderer's Desk did not appear within 8 seconds")
