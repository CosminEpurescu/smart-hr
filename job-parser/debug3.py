#!/usr/bin/env python3
"""Debug pagination endpoint."""

import requests
from bs4 import BeautifulSoup
import re

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Accept': '*/*',
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': 'https://careers.ing.com/en/search-jobs',
}

# Test different URL formats for pagination
urls_to_test = [
    'https://careers.ing.com/en/search-jobs/results?p=1',
    'https://careers.ing.com/en/search-jobs/results?p=2',
    'https://careers.ing.com/search-jobs/results?p=1',
    'https://careers.ing.com/en/search-jobs?p=2',
]

for url in urls_to_test:
    print(f"\n=== Testing: {url} ===")
    resp = requests.get(url, headers=headers)
    print(f'Status: {resp.status_code}')
    
    if resp.status_code == 200:
        try:
            data = resp.json()
            print(f'JSON keys: {list(data.keys())}')
            if data.get('results'):
                soup = BeautifulSoup(data['results'], 'lxml')
                links = soup.find_all('a', href=re.compile(r'/en/job/'))
                print(f'Job links in results: {len(links)}')
        except:
            print(f'Not JSON, length: {len(resp.text)}')
            if len(resp.text) > 1000:
                soup = BeautifulSoup(resp.text, 'lxml')
                links = soup.find_all('a', href=re.compile(r'/en/job/'))
                print(f'Job links in HTML: {len(links)}')
