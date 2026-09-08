#!/usr/bin/env python3
"""Quan's loopback-only desktop dashboard. Python standard library only."""
import concurrent.futures
import datetime as dt
import email.utils
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import wanderer_feeds
import wanderer_theme
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parent
HOME = Path.home()
PORT = int(os.environ.get('QUAN_DASHBOARD_PORT', '8990'))
ORIGIN = f'http://127.0.0.1:{PORT}'
CONFIG = ROOT / 'settings.json'
LOCK = threading.Lock()
CACHE = {}
CPU = None
FEEDS = [('Hugging Face', 'https://huggingface.co/blog/feed.xml'), ('OpenAI', 'https://openai.com/news/rss.xml')]

def settings():
    try:
        return json.loads(CONFIG.read_text())
    except (OSError, ValueError):
        return {'news': True, 'city': '', 'units': 'fahrenheit'}

def fetch(url, data=None, timeout=12):
    headers = {'User-Agent': 'QuanWorkbench/1.0', 'Accept': 'application/json, application/xml, text/xml'}
    if data is not None:
        data = json.dumps(data).encode()
        headers['Content-Type'] = 'application/json'
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=timeout) as res:
        return res.read(4_000_000)

def cached(key, ttl, fn):
    with LOCK:
        hit = CACHE.get(key)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    result = fn()
    with LOCK:
        CACHE[key] = (time.time(), result)
    return result

def machine():
    global CPU
    nums = [int(x) for x in Path('/proc/stat').read_text().splitlines()[0].split()[1:9]]
    current = (sum(nums), nums[3] + nums[4])
    with LOCK:
        prior, CPU = CPU, current
    cpu = None if not prior or current[0] == prior[0] else round(100 * (1 - (current[1]-prior[1])/(current[0]-prior[0])), 1)
    mem = {line.split(':')[0]: int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines()}
    disk = shutil.disk_usage(HOME)
    agents = []
    for proc in Path('/proc').glob('[0-9]*'):
        try:
            if proc.stat().st_uid != os.getuid():
                continue
            name = (proc/'comm').read_text().strip()
            if name in ('codex', 'claude', 'opencode', 'ollama'):
                agents.append({'name': name, 'pid': int(proc.name)})
        except OSError:
            pass
    temps = []
    for hw in Path('/sys/class/hwmon').glob('hwmon*'):
        try:
            if (hw/'name').read_text().strip() == 'k10temp':
                temps = [int(p.read_text())/1000 for p in hw.glob('temp*_input')]
        except OSError:
            pass
    return {'cpu': cpu, 'ramUsed': mem['MemTotal']-mem['MemAvailable'], 'ramTotal': mem['MemTotal'], 'diskFree': disk.free, 'diskTotal': disk.total, 'temperature': max(temps) if temps else None, 'uptime': int(float(Path('/proc/uptime').read_text().split()[0])), 'agents': agents, 'sampledAt': time.time()}

def local_models():
    try:
        data = json.loads(fetch('http://127.0.0.1:11434/api/tags', timeout=2))
        models = [m for m in data.get('models', []) if not m.get('remote_host') and not m.get('remote_model') and 'cloud' not in m['name']]
        running = json.loads(fetch('http://127.0.0.1:11434/api/ps', timeout=2)).get('models', [])
        return {'online': True, 'models': [{'name': m['name'], 'size': m['size']} for m in models], 'running': [m['name'] for m in running]}
    except Exception:
        return {'online': False, 'models': [], 'running': []}

def news():
    if not settings().get('news'):
        return {'items': [], 'disabled': True}
    def collect():
        items, errors = [], []
        def feed(source):
            name, url = source
            doc = ET.fromstring(fetch(url))
            rows = []
            for item in doc.findall('.//item')[:8]:
                link = item.findtext('link', '')
                if urllib.parse.urlparse(link).scheme != 'https':
                    continue
                published = item.findtext('pubDate', '')
                try:
                    stamp = email.utils.parsedate_to_datetime(published).timestamp()
                except (ValueError, TypeError):
                    stamp = 0
                rows.append({'title': item.findtext('title', '').strip(), 'url': link, 'source': name, 'published': stamp})
            return rows
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            jobs = {pool.submit(feed, f): f[0] for f in FEEDS}
            for job, source in jobs.items():
                try:
                    items.extend(job.result())
                except Exception:
                    errors.append(source)
        return {'items': sorted(items, key=lambda x: x['published'], reverse=True)[:10], 'errors': errors, 'updated': time.time()}
    return cached('news', 1800, collect)

def weather():
    cfg = settings()
    city = cfg.get('city', '').strip()
    if not city:
        return {'needsCity': True}
    def collect():
        geo = json.loads(fetch('https://geocoding-api.open-meteo.com/v1/search?' + urllib.parse.urlencode({'name': city, 'count': 1, 'language': 'en', 'format': 'json'})))
        places = geo.get('results', [])
        if not places:
            return {'error': 'City not found. Try a nearby city.'}
        place = places[0]
        query = {'latitude': place['latitude'], 'longitude': place['longitude'], 'current': 'temperature_2m,apparent_temperature,weather_code,wind_speed_10m', 'daily': 'temperature_2m_max,temperature_2m_min,precipitation_probability_max', 'forecast_days': 3, 'timezone': 'auto', 'temperature_unit': cfg['units'], 'wind_speed_unit': 'mph' if cfg['units']=='fahrenheit' else 'kmh'}
        data = json.loads(fetch('https://api.open-meteo.com/v1/forecast?' + urllib.parse.urlencode(query)))
        return {'place': ', '.join(str(place[k]) for k in ('name','admin1') if place.get(k)), 'current': data['current'], 'units': data['current_units'], 'daily': data['daily'], 'updated': time.time()}
    return cached(('weather', city, cfg['units']), 900, collect)

def launch(action):
    codex = shutil.which('codex') or 'codex'
    work = HOME/'Work' if (HOME/'Work').is_dir() else HOME
    terminal = ['foot', '--hold', '--working-directory='+str(work)]
    commands = {
        'resume': terminal + [str(codex), 'resume', '--all'],
        'agent': terminal + [str(codex)],
        'local-agent': terminal + [str(codex), '--oss', '--local-provider', 'ollama', '-m', 'qwen3.5:4b', '-c', 'model_context_window=4096', '-c', 'model_reasoning_effort="none"'],
        'terminal': ['foot', '--working-directory='+str(work)],
        'files': ['xdg-open', str(work)],
        'monitor': terminal + ['btop'],
    }
    if action not in commands:
        raise ValueError('Unknown action')
    if action == 'local-agent' and not any(m['name']=='qwen3.5:4b' for m in local_models()['models']):
        raise ValueError('The local model is still being set up.')
    subprocess.Popen(commands[action], start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return {'ok': True}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass
    def send(self, data, status=200, kind='application/json'):
        raw = json.dumps(data).encode() if kind=='application/json' and not isinstance(data, bytes) else data
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(raw)
    def trusted(self):
        return self.headers.get('Host') == f'127.0.0.1:{PORT}'
    def do_GET(self):
        if not self.trusted():
            return self.send({'error': 'Invalid host'}, 403)
        route = urllib.parse.urlsplit(self.path).path
        try:
            if route == '/wanderer/theme.css':
                return self.send(wanderer_theme.stylesheet(), kind='text/css')
            handlers = {'/api/machine': machine, '/api/models': local_models, '/api/news': news, '/api/weather': weather, '/api/settings': settings, '/api/wanderer/news': wanderer_feeds.news}
            if route in handlers:
                return self.send(handlers[route]())
            files = {'/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js','text/javascript'), '/style.css': ('style.css','text/css'), '/wallpaper.png': ('wallpaper.png', 'image/png')}
            for name, mime in [('index.html', 'text/html; charset=utf-8'), ('app.js', 'text/javascript'), ('style.css', 'text/css'), ('readings.json', 'application/json')]:
                files['/wanderer/' + name] = ('wanderer/' + name, mime)
            files['/wanderer/'] = files['/wanderer/index.html']
            if route not in files:
                return self.send({'error': 'Not found'},404)
            path, kind = files[route]
            self.send((ROOT/path).read_bytes(), kind=kind)
        except Exception:
            self.send({'error': 'This readout is temporarily unavailable. Try again shortly.'}, 503)
    def do_POST(self):
        if not self.trusted() or self.headers.get('Origin') != ORIGIN or self.headers.get('Content-Type') != 'application/json':
            return self.send({'error': 'Request rejected'},403)
        try:
            size = int(self.headers.get('Content-Length', 0))
            if not 0 < size <= 65536:
                return self.send({'error': 'Request too large'},413)
            data = json.loads(self.rfile.read(size))
            if self.path == '/api/action':
                return self.send(launch(data.get('action')))
            if self.path == '/api/settings':
                city = data.get('city', '')
                units = data.get('units')
                if not isinstance(city, str) or len(city)>100 or units not in ('fahrenheit','celsius') or type(data.get('news')) is not bool:
                    raise ValueError('Check your settings.')
                cfg = {'city': city.strip(), 'units': units, 'news': data['news']}
                with LOCK:
                    tmp = CONFIG.with_suffix('.tmp')
                    tmp.write_text(json.dumps(cfg, indent=2)+'\n')
                    tmp.replace(CONFIG)
                return self.send(cfg)
            if self.path == '/api/chat':
                model = data.get('model')
                if model not in [m['name'] for m in local_models()['models']]:
                    raise ValueError('Choose a downloaded local model.')
                messages = data.get('messages', [])
                if not isinstance(messages,list) or not 1 <= len(messages) <= 20 or any(m.get('role') not in ('user','assistant') or not isinstance(m.get('content'),str) or len(m['content'])>8000 for m in messages):
                    raise ValueError('Message is too long. Start a fresh chat.')
                result = json.loads(fetch('http://127.0.0.1:11434/api/chat', {'model':model, 'messages':messages,'stream':False,'think':False,'options':{'num_ctx':4096,'num_predict':512},'keep_alive':'5m'}, timeout=180))
                return self.send({'reply': result['message']['content'], 'tokens': result.get('eval_count',0), 'seconds': round(result.get('total_duration',0)/1e9,1)})
            self.send({'error':'Not found'},404)
        except (ValueError, TypeError, KeyError, AttributeError) as e:
            self.send({'error':str(e)},400)
        except Exception:
            self.send({'error':'The local service could not finish. Check that Ollama is running and try again.'},503)

if __name__ == '__main__':
    ThreadingHTTPServer(('127.0.0.1',PORT), Handler).serve_forever()
