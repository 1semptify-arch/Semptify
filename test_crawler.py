"""
Semptify Automated Page Crawler & Error Finder
Crawls every page, tests links, finds errors, generates report.
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
from datetime import datetime
from collections import defaultdict

BASE_URL = "http://localhost:8000"
VISITED = set()
ERRORS = []
PAGES_FOUND = []
BROKEN_LINKS = []
NAVIGATION_ISSUES = []
PAGE_DETAILS = {}

async def fetch_page(session, url):
    """Fetch a page and return status + content."""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            content = await response.text()
            return {
                'url': url,
                'status': response.status,
                'content': content,
                'ok': response.status == 200
            }
    except Exception as e:
        return {
            'url': url,
            'status': 0,
            'content': '',
            'ok': False,
            'error': str(e)
        }

def extract_links(html, base_url):
    """Extract all links from HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    links = set()
    
    # Find all anchor tags
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.startswith('#') or href.startswith('javascript:'):
            continue
        if href.startswith('mailto:') or href.startswith('tel:'):
            continue
        
        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)
        
        # Only follow internal links
        if parsed.netloc in ['localhost:8000', '127.0.0.1:8000', '']:
            links.add(full_url)
    
    return links

def analyze_page(html, url):
    """Analyze a page for common issues."""
    issues = []
    soup = BeautifulSoup(html, 'html.parser')
    
    # Check for multiple navbars (ignore hidden ones)
    def is_visible(elem):
        """Check if element is not hidden via style attribute"""
        style = elem.get('style', '')
        if 'display:none' in style.replace(' ', '').lower():
            return False
        if 'display: none' in style.lower():
            return False
        return True
    
    navs = [n for n in soup.find_all('nav') if is_visible(n)]
    nav_divs = soup.find_all('div', id='semptify-nav')
    sidebars = soup.find_all(class_=lambda x: x and 'sidebar' in x.lower() if x else False)
    
    # Filter visible sidebars
    visible_sidebars = [s for s in sidebars if is_visible(s)]
    
    nav_count = len(navs) + len(nav_divs)
    if nav_count > 1:
        issues.append(f"Multiple visible navigation elements found ({nav_count})")
    
    # Check for auth-strip (should be removed)
    auth_strips = soup.find_all(id='auth-strip-container')
    if auth_strips:
        issues.append("Old auth-strip component still present")
    
    # Check for header.js loading
    scripts = soup.find_all('script', src=True)
    for script in scripts:
        if 'header.js' in script['src']:
            # Check if page also has semptify-nav
            if nav_divs:
                issues.append("Both header.js AND semptify-nav loaded (duplicate nav)")
    
    # Check for broken images
    for img in soup.find_all('img', src=True):
        src = img['src']
        if not src.startswith('data:') and not src.startswith('http'):
            # It's a local image - we'll check these later
            pass
    
    # Check for empty/placeholder content
    title = soup.find('title')
    if title and ('Loading' in title.text or 'Untitled' in title.text):
        issues.append(f"Page has placeholder title: {title.text}")
    
    # Check for JavaScript errors in inline scripts (basic check)
    inline_scripts = soup.find_all('script', src=False)
    for script in inline_scripts:
        if script.string:
            if 'undefined' in script.string and 'typeof' not in script.string:
                issues.append("Potential undefined reference in inline script")
    
    return issues

async def crawl(session, url, depth=0, max_depth=3):
    """Recursively crawl pages."""
    if url in VISITED or depth > max_depth:
        return
    
    # Skip non-HTML resources
    if any(url.endswith(ext) for ext in ['.js', '.css', '.png', '.jpg', '.ico', '.svg', '.woff', '.woff2']):
        return
    
    VISITED.add(url)
    print(f"  Crawling: {url}")
    
    result = await fetch_page(session, url)
    
    page_info = {
        'url': url,
        'status': result['status'],
        'issues': []
    }
    
    if not result['ok']:
        error_msg = result.get('error', f"HTTP {result['status']}")
        BROKEN_LINKS.append({
            'url': url,
            'error': error_msg
        })
        page_info['issues'].append(f"Page error: {error_msg}")
    else:
        PAGES_FOUND.append(url)
        
        # Analyze page for issues
        issues = analyze_page(result['content'], url)
        page_info['issues'] = issues
        if issues:
            NAVIGATION_ISSUES.append({
                'url': url,
                'issues': issues
            })
        
        # Extract and follow links
        links = extract_links(result['content'], url)
        for link in links:
            if link not in VISITED:
                await crawl(session, link, depth + 1, max_depth)
    
    PAGE_DETAILS[url] = page_info

async def test_api_endpoints(session):
    """Test common API endpoints."""
    print("\n📡 Testing API Endpoints...")
    
    api_endpoints = [
        '/api/documents/',
        '/api/timeline/',
        '/api/eviction-defense/defenses',
        '/api/eviction-defense/motions',
        '/storage/status',
        '/api/law-library/categories',
        '/api/law-library/statutes',
        '/api/emotion/state',
    ]
    
    api_results = []
    for endpoint in api_endpoints:
        url = BASE_URL + endpoint
        result = await fetch_page(session, url)
        status = "✅" if result['ok'] else "❌"
        api_results.append({
            'endpoint': endpoint,
            'status': result['status'],
            'ok': result['ok']
        })
        print(f"  {status} {endpoint} - {result['status']}")
    
    return api_results

async def main():
    """Main crawler function."""
    print("=" * 60)
    print("🔍 SEMPTIFY AUTOMATED PAGE CRAWLER")
    print("=" * 60)
    print(f"Starting crawl from: {BASE_URL}")
    print()
    
    # Starting pages
    start_pages = [
        f"{BASE_URL}/static/welcome.html",
        f"{BASE_URL}/static/dashboard.html",
        f"{BASE_URL}/static/document_intake.html",
    ]
    
    async with aiohttp.ClientSession() as session:
        # First, test if server is running
        test = await fetch_page(session, BASE_URL)
        if not test['ok'] and test['status'] == 0:
            print("❌ ERROR: Server not running at localhost:8000")
            print("   Start the server first: python -m uvicorn app.main:app --port 8000")
            return
        
        print("🌐 Crawling pages...")
        for start_url in start_pages:
            await crawl(session, start_url)
        
        # Test API endpoints
        api_results = await test_api_endpoints(session)
    
    # Generate Report
    print()
    print("=" * 60)
    print("📊 CRAWL REPORT")
    print("=" * 60)
    
    print(f"\n✅ Pages Found: {len(PAGES_FOUND)}")
    for page in sorted(PAGES_FOUND):
        short = page.replace(BASE_URL, '')
        print(f"   • {short}")
    
    print(f"\n❌ Broken Links: {len(BROKEN_LINKS)}")
    for item in BROKEN_LINKS:
        short = item['url'].replace(BASE_URL, '')
        print(f"   • {short} - {item['error']}")
    
    print(f"\n⚠️  Navigation/Layout Issues: {len(NAVIGATION_ISSUES)}")
    for item in NAVIGATION_ISSUES:
        short = item['url'].replace(BASE_URL, '')
        print(f"   • {short}")
        for issue in item['issues']:
            print(f"      - {issue}")
    
    # Save detailed report
    report = {
        'timestamp': datetime.now().isoformat(),
        'base_url': BASE_URL,
        'pages_found': len(PAGES_FOUND),
        'broken_links': BROKEN_LINKS,
        'navigation_issues': NAVIGATION_ISSUES,
        'all_pages': PAGE_DETAILS,
        'api_results': api_results
    }
    
    with open('crawler_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print()
    print("=" * 60)
    print("📁 Full report saved to: crawler_report.json")
    print("=" * 60)
    
    # Summary for fixing
    if NAVIGATION_ISSUES or BROKEN_LINKS:
        print()
        print("🔧 ISSUES TO FIX:")
        print("-" * 40)
        
        all_issues = []
        for item in NAVIGATION_ISSUES:
            for issue in item['issues']:
                all_issues.append(f"{item['url'].replace(BASE_URL, '')}: {issue}")
        
        for item in BROKEN_LINKS:
            all_issues.append(f"BROKEN: {item['url'].replace(BASE_URL, '')} - {item['error']}")
        
        for i, issue in enumerate(all_issues, 1):
            print(f"{i}. {issue}")
    else:
        print("\n✅ No issues found! All pages look good.")

if __name__ == "__main__":
    asyncio.run(main())
