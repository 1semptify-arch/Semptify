#!/usr/bin/env python3
"""Test nav links on authenticated pages (that use base.html nav block)."""

import requests

base = 'http://127.0.0.1:8000'

pages_to_check = [
    ('/documents', 'documents.html'),
    ('/timeline', 'timeline.html'),
    ('/functionx', 'functionx.html'),
    ('/law-library', 'law-library'),
]

print('=== Checking nav links on authenticated pages ===\n')

for url, page_name in pages_to_check:
    try:
        resp = requests.get(f'{base}{url}', allow_redirects=True, timeout=5)
        if resp.status_code == 200:
            html = resp.text.lower()
            has_calendar = '/calendar' in html
            has_eviction = '/eviction-defense' in html
            
            print(f'{page_name:25} /calendar:{has_calendar:5}  /eviction-defense:{has_eviction:5}')
        else:
            print(f'{page_name:25} Status {resp.status_code}')
    except Exception as e:
        print(f'{page_name:25} Error: {e}')

print('\nNote: Pages with role guards may redirector return different HTML.')
print('The key test is: do the nav links appear in ANY rendered page?')
