#!/usr/bin/env python3
"""Debug script to test ING API."""

import requests
import json

url = 'https://careers.ing.com/en/search-jobs/results'
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Accept': '*/*',
    'X-Requested-With': 'XMLHttpRequest',
}

params = {
    'CurrentPage': 1,
    'RecordsPerPage': 15,
}

resp = requests.get(url, params=params, headers=headers)
print('Status:', resp.status_code)
print('Content-Type:', resp.headers.get('content-type'))
print('Response length:', len(resp.text))
print()

try:
    data = resp.json()
    print('JSON Keys:', list(data.keys()))
    if 'totalCount' in data:
        print('Total Count:', data['totalCount'])
    if 'results' in data:
        print('Results type:', type(data['results']))
        if data['results']:
            print('Results preview:', data['results'][:500])
        else:
            print('Results: Empty')
except Exception as e:
    print(f'Error: {e}')
    print('Not JSON, first 1000 chars:')
    print(resp.text[:1000])
