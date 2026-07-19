"""
Comprehensive HTML Link Validator
Tests every link from every HTML page end-to-end.
Extracts href, src, action, onclick, and data-* links.
"""

import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import requests

BASE_URL = "http://localhost:8000"
TEMPLATES_DIR = Path("c:/Semptify/Semptify-FastAPI/app/templates")

# Skip node_modules and design-system
SKIP_DIRS = {"node_modules", "design-system", "recipe_visualizations"}

# Link patterns to extract
LINK_PATTERNS = [
    (r'href=["\']([^"\']+)["\']', "href"),
    (r'src=["\']([^"\']+)["\']', "src"),
    (r'action=["\']([^"\']+)["\']', "action"),
    (r'onclick=["\']([^"\']+)["\']', "onclick"),
    (r'data-[^=]*=["\']([^"\']+)["\']', "data-*"),
    (r'url\(["\']?([^"\')]+)["\']?\)', "css url"),
    (r'window\.location\s*=\s*["\']([^"\']+)["\']', "window.location"),
    (r'window\.location\.href\s*=\s*["\']([^"\']+)["\']', "window.location.href"),
    (r'fetch\(["\']([^"\']+)["\']', "fetch"),
    (r'\.get\(["\']([^"\']+)["\']', ".get"),
    (r'\.post\(["\']([^"\']+)["\']', ".post"),
]


def extract_links_from_file(html_file: Path) -> list[tuple[str, str, int]]:
    """Extract all links from an HTML file with line numbers."""
    links = []
    content = html_file.read_text(encoding="utf-8", errors="ignore")
    lines = content.split("\n")

    for line_num, line in enumerate(lines, 1):
        for pattern, link_type in LINK_PATTERNS:
            matches = re.finditer(pattern, line, re.IGNORECASE)
            for match in matches:
                link = match.group(1)
                # Skip empty, anchors, javascript:, mailto:, tel:
                if (
                    not link
                    or link.startswith("#")
                    or link.startswith("javascript:")
                    or link.startswith("mailto:")
                    or link.startswith("tel:")
                ):
                    continue
                # Skip Jinja2 expressions
                if "{{" in link or "{%" in link:
                    continue
                links.append((link, link_type, line_num))

    return links


def normalize_link(link: str, base_url: str = BASE_URL) -> str:
    """Normalize a link to a full URL."""
    if link.startswith("http://") or link.startswith("https://"):
        return link
    if link.startswith("/"):
        return urljoin(base_url, link)
    return urljoin(base_url + "/", link)


def test_link(url: str, timeout: int = 5) -> tuple[bool, int, str]:
    """Test a single link. Returns (success, status_code, error)."""
    try:
        # Skip external URLs
        if not url.startswith(BASE_URL):
            return (True, 0, "external")

        # Determine HTTP method based on URL pattern
        method = "GET"
        if (
            "/function-token/issue" in url
            or "/validate" in url
            or "/toggle" in url
            or "/upload" in url
            or "/capture" in url
            or "/advance" in url
        ):
            method = "POST"

        if method == "POST":
            response = requests.post(url, timeout=timeout, allow_redirects=True)
        else:
            response = requests.get(url, timeout=timeout, allow_redirects=True)

        # 401 is expected for authenticated endpoints
        if response.status_code == 401:
            return (True, 401, "authenticated")

        return (response.status_code < 400, response.status_code, "")
    except requests.exceptions.Timeout:
        return (False, 0, "timeout")
    except requests.exceptions.ConnectionError:
        return (False, 0, "connection_error")
    except Exception as e:
        return (False, 0, str(e))


def find_all_html_files() -> list[Path]:
    """Find all HTML files in templates directory."""
    html_files = []
    for html_file in TEMPLATES_DIR.rglob("*.html"):
        # Skip directories in SKIP_DIRS
        if any(skip_dir in str(html_file) for skip_dir in SKIP_DIRS):
            continue
        html_files.append(html_file)
    return html_files


def main():
    print("=" * 80)
    print("COMPREHENSIVE HTML LINK VALIDATOR")
    print("=" * 80)
    print(f"Base URL: {BASE_URL}")
    print(f"Templates Dir: {TEMPLATES_DIR}")
    print()

    # Find all HTML files
    html_files = find_all_html_files()
    print(f"Found {len(html_files)} HTML files to scan")
    print()

    # Extract all links
    all_links = []
    for html_file in html_files:
        rel_path = html_file.relative_to(TEMPLATES_DIR)
        links = extract_links_from_file(html_file)
        for link, link_type, line_num in links:
            all_links.append(
                {
                    "file": str(rel_path),
                    "link": link,
                    "type": link_type,
                    "line": line_num,
                }
            )

    print(f"Extracted {len(all_links)} links")
    print()

    # Deduplicate links
    unique_links = {}
    for item in all_links:
        link = item["link"]
        if link not in unique_links:
            unique_links[link] = []
        unique_links[link].append(item)

    print(f"Unique links to test: {len(unique_links)}")
    print()

    # Test each unique link
    results = []
    broken_links = []

    for i, (link, sources) in enumerate(unique_links.items(), 1):
        url = normalize_link(link)
        success, status_code, error = test_link(url)

        result = {
            "link": link,
            "url": url,
            "success": success,
            "status_code": status_code,
            "error": error,
            "sources": sources,
        }
        results.append(result)

        if not success:
            broken_links.append(result)

        # Progress
        if i % 10 == 0:
            print(f"Tested {i}/{len(unique_links)} links... ({len(broken_links)} broken so far)")

        # Small delay to avoid overwhelming server
        time.sleep(0.05)

    print()
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Total unique links tested: {len(results)}")
    print(f"Successful: {len([r for r in results if r['success']])}")
    print(f"Broken: {len(broken_links)}")
    print()

    if broken_links:
        print("=" * 80)
        print("BROKEN LINKS")
        print("=" * 80)
        for broken in broken_links:
            print(f"\nLink: {broken['link']}")
            print(f"URL: {broken['url']}")
            print(f"Status: {broken['status_code']} ({broken['error']})")
            print("Found in:")
            for source in broken["sources"]:
                print(f"  - {source['file']}:{source['line']} ({source['type']})")

        # Save broken links to file
        output_file = Path("c:/Semptify/Semptify-FastAPI/broken_links_report.json")
        with output_file.open("w") as f:
            json.dump(broken_links, f, indent=2)
        print(f"\nBroken links saved to: {output_file}")
    else:
        print("✅ ALL LINKS ARE WORKING!")

    # Save full results
    output_file = Path("c:/Semptify/Semptify-FastAPI/link_test_results.json")
    with output_file.open("w") as f:
        json.dump(results, f, indent=2)
    print(f"\nFull results saved to: {output_file}")


if __name__ == "__main__":
    main()
