"""Public publisher feeds for Wanderer's Desk; no third-party packages."""
import concurrent.futures
import email.utils
import datetime
import threading
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

FEEDS = [
    ('arXiv · AI', 'https://rss.arxiv.org/rss/cs.AI', 'Research preprint'),
    ('arXiv · neuroscience', 'https://rss.arxiv.org/rss/q-bio.NC', 'Research preprint'),
    ('arXiv · sound', 'https://rss.arxiv.org/rss/cs.SD', 'Research preprint'),
    ('Hugging Face', 'https://huggingface.co/blog/feed.xml', 'AI development · publisher blog'),
]
LOCK = threading.Lock()
CACHE = None

def parse(raw, name, kind):
    doc = ET.fromstring(raw)
    result = []
    for row in doc.findall('.//item')[:4]:
        url = row.findtext('link', '').strip()
        if urllib.parse.urlsplit(url).scheme != 'https':
            continue
        date = row.findtext('pubDate', '').strip()
        try:
            date = email.utils.parsedate_to_datetime(date).date().isoformat()
        except (ValueError, TypeError, AttributeError):
            date = ''
        result.append({'source': name, 'kind': kind, 'title': row.findtext('title', '').strip(), 'url': url, 'date': date})
    return result

def news():
    global CACHE
    with LOCK:
        if CACHE and time.time() - CACHE['checkedAt'] < 1800:
            return CACHE
        def fetch(feed):
            name, url, kind = feed
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'WanderersDesk/1.0 (personal RSS reader)'})
                with urllib.request.urlopen(req, timeout=12) as response:
                    return parse(response.read(2_000_000), name, kind), None
            except Exception:
                return [], name
        items, errors = [], []
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            for rows, error in pool.map(fetch, FEEDS):
                items.extend(rows)
                if error:
                    errors.append(error)
        CACHE = {'items': sorted(items, key=lambda r: r['date'], reverse=True), 'errors': errors, 'checkedAt': time.time()}
        return CACHE
