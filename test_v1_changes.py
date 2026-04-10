#!/usr/bin/env python3
"""Quick test of V1 changes: calendar route, nav links, OAuth redirect."""

import requests

base = 'http://127.0.0.1:8000'

# Test 1: Check unauthenticated nav redirects to /storage/providers
print('=== Test 1: Unauthenticated nav endpoint ===')
try:
    resp = requests.get(f'{base}/ui/navigation', allow_redirects=True, timeout=5)
    if resp.status_code == 200:
        data = resp.json()
        menu = data.get('menu', [])
        sign_in = next((m for m in menu if 'Sign In' in m.get('label', '')), None)
        if sign_in:
            path = sign_in.get('path')
            if path == '/storage/providers':
                print('✓ PASS: Sign In link points to /storage/providers')
            else:
                print(f'✗ FAIL: Sign In link points to {path} (expected /storage/providers)')
        else:
            print('✗ FAIL: Sign In menu item not found')
    else:
        print(f'✗ FAIL: Status {resp.status_code}')
except Exception as e:
    print(f'✗ FAIL: {e}')

# Test 2: Verify /calendar route exists
print('\n=== Test 2: Calendar route ===')
try:
    resp = requests.get(f'{base}/calendar', allow_redirects=True, timeout=5)
    if resp.status_code == 200:
        print('✓ PASS: /calendar returns 200')
    else:
        print(f'✗ FAIL: /calendar returned {resp.status_code}')
except Exception as e:
    print(f'✗ FAIL: {e}')

# Test 3: Check /storage/providers page loads
print('\n=== Test 3: Storage providers page ===')
try:
    resp = requests.get(f'{base}/storage/providers', allow_redirects=True, timeout=5)
    if resp.status_code == 200:
        print('✓ PASS: /storage/providers loads (200 OK)')
    else:
        print(f'✗ FAIL: /storage/providers returned {resp.status_code}')
except Exception as e:
    print(f'✗ FAIL: {e}')

# Test 4: Verify base nav links
print('\n=== Test 4: Base nav links ===')
try:
    resp = requests.get(f'{base}/', allow_redirects=True, timeout=5)
    html = resp.text.lower()
    
    calendar_ok = '/calendar' in html
    eviction_ok = '/eviction-defense' in html
    
    if calendar_ok:
        print('✓ PASS: /calendar link in nav')
    else:
        print('✗ FAIL: /calendar link missing')
    
    if eviction_ok:
        print('✓ PASS: /eviction-defense link in nav')
    else:
        print('✗ FAIL: /eviction-defense link missing')
except Exception as e:
    print(f'✗ FAIL: {e}')

print('\n=== Summary ===')
print('All tests completed. Check results above.')
