#!/usr/bin/env python3
"""Test scraping multiple pages."""

import requests
from bs4 import BeautifulSoup
import re
import time

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

all_jobs = set()

for page in range(1, 6):  # Test first 5 pages
    url = f'https://careers.ing.com/en/search-jobs?p={page}'
    print(f"\n=== Page {page} ===")
    
    resp = requests.get(url, headers=headers)
    print(f'Status: {resp.status_code}')
    
    soup = BeautifulSoup(resp.text, 'lxml')
    
    # Get job count from header
    for h2 in soup.find_all('h2'):
        text = h2.get_text(strip=True)
        if 'jobs' in text.lower() and 'have' in text.lower():
            print(f'Header: {text}')
            break
    
    # Find job links
    job_links = soup.find_all('a', href=re.compile(r'/en/job/[^/]+/[^/]+/\d+/\d+'))
    
    page_jobs = set()
    for link in job_links:
        href = link.get('href', '')
        if '/en/job/' in href:
            page_jobs.add(href)
    
    new_jobs = page_jobs - all_jobs
    all_jobs.update(page_jobs)
    
    print(f'Jobs on this page: {len(page_jobs)}')
    print(f'New jobs: {len(new_jobs)}')
    print(f'Total unique jobs so far: {len(all_jobs)}')
    
    if len(new_jobs) == 0:
        print("No new jobs found, stopping...")
        break
    
    time.sleep(0.5)

print(f'\n=== TOTAL UNIQUE JOBS: {len(all_jobs)} ===')
