"""Print today's reading for the desktop card."""
import datetime
import json
from pathlib import Path
readings = json.loads(Path(__file__).with_name('readings.json').read_text())
print(json.dumps(readings[(datetime.date.today() - datetime.date(1970, 1, 1)).days % len(readings)] if readings else {}))
