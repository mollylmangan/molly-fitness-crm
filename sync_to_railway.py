#!/usr/bin/env python3
"""
sync_to_railway.py
Pushes local data/fitness_leads.json + data/tasks.json to your Railway app.

Usage:
    python3 sync_to_railway.py

Set RAILWAY_URL and ADMIN_KEY in your local .env before running.
"""

import json, os, urllib.request, urllib.error

_env = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(_env):
    with open(_env) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

RAILWAY_URL = os.environ.get('RAILWAY_URL', '').rstrip('/')
ADMIN_KEY   = os.environ.get('ADMIN_KEY', '')

if not RAILWAY_URL:
    print('❌  Set RAILWAY_URL=https://your-app.up.railway.app in .env')
    exit(1)
if not ADMIN_KEY:
    print('❌  Set ADMIN_KEY in .env (must match the Railway env var)')
    exit(1)

BASE = os.path.dirname(os.path.abspath(__file__))

def read(name):
    path = os.path.join(BASE, 'data', name)
    with open(path) as f: return json.load(f)

payload = json.dumps({
    'leads': read('fitness_leads.json'),
    'tasks': read('tasks.json'),
}).encode()

req = urllib.request.Request(
    f'{RAILWAY_URL}/api/admin/sync',
    data=payload,
    headers={'Content-Type': 'application/json', 'X-Admin-Key': ADMIN_KEY},
    method='POST'
)

try:
    with urllib.request.urlopen(req, timeout=30) as res:
        body = json.loads(res.read())
        print(f'✅  Synced → {body["leads"]} leads, {body["tasks"]} tasks')
except urllib.error.HTTPError as e:
    print(f'❌  HTTP {e.code}: {e.read().decode()}')
except Exception as e:
    print(f'❌  Error: {e}')
