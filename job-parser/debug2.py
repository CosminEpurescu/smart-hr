#!/usr/bin/env python3
"""Debug script to test ING careers page scraping."""

import requests
from bs4 import BeautifulSoup
import re

print("=== Testing Main Search Page ===")
url = 'https://careers.ing.com/en/search-jobs'
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

resp = requests.get(url, headers=headers)
print(f'Status: {resp.status_code}')
print(f'Response length: {len(resp.text)}')

soup = BeautifulSoup(resp.text, 'lxml')

# Find job count
for h2 in soup.find_all('h2'):
    if 'jobs' in h2.get_text().lower():
        print(f'Header: {h2.get_text(strip=True)}')

# Find all job links
job_links = soup.find_all('a', href=re.compile(r'/en/job/'))
print(f'Found {len(job_links)} job links')

seen = set()
for link in job_links:
    href = link.get('href', '')
    if '/en/job/' in href and href not in seen:
        seen.add(href)
        title = link.get_text(strip=True)
        if title and title not in ['Show job', 'View job', 'Apply now']:
            if len(seen) <= 10:
                print(f'  - {title}')

print(f'\nTotal unique job URLs: {len(seen)}')
