# app/crawlers/plainsite.py
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

BASE_URL = "https://www.plainsite.org"
SEARCH_URL = f"{BASE_URL}/search/"


async def fetch_plainsite_profile(attorney_name: str) -> dict:
    """
    Fetch attorney or entity profile from PlainSite.

    PlainSite provides litigation history, attorney profiles, and cross-state case information.
    """
    async with httpx.AsyncClient() as client:
        params = {"q": attorney_name}
        resp = await client.get(SEARCH_URL, params=params, follow_redirects=True)
        html = resp.text
        soup = BeautifulSoup(html, "html.parser")

        results = []

        # Look for search results - PlainSite typically uses list items or cards
        result_selectors = [
            "div.search-result",
            "div.result",
            "li.result",
            "article",
            "div[class*='result']",
            "div[class*='item']",
        ]

        result_elements = []
        for selector in result_selectors:
            result_elements = soup.select(selector)
            if result_elements:
                break

        # If no structured results, try to find any links that look like case/attorney pages
        if not result_elements:
            result_elements = soup.find_all("a", href=True)

        for element in result_elements:
            try:
                if element.name == "a":
                    # It's a direct link
                    link = element
                    title = link.get_text(strip=True)
                    href = link.get("href")
                    if not href or not title:
                        continue
                else:
                    # It's a container element
                    link = element.find("a", href=True)
                    if not link:
                        continue
                    title = link.get_text(strip=True)
                    href = link.get("href")
                    if not href or not title:
                        continue

                # Make URL absolute
                full_url = urljoin(BASE_URL, href)

                # Extract basic info from the result
                result = {
                    "title": title,
                    "url": full_url,
                    "type": "unknown",
                }

                # Try to determine if it's an attorney, case, or entity
                title_lower = title.lower()
                if "v." in title or "vs." in title or "case" in title_lower:
                    result["type"] = "case"
                elif any(word in title_lower for word in ["llc", "inc", "corp", "company"]):
                    result["type"] = "entity"
                elif any(word in title_lower for word in ["attorney", "law", "esq"]):
                    result["type"] = "attorney"

                results.append(result)

            except Exception:
                continue

        return {
            "query": attorney_name,
            "results": results[:20],  # Limit to top 20 results
            "total_results": len(results),
        }


async def fetch_plainsite_case_detail(url: str) -> dict | None:
    """
    Fetch detailed case information from PlainSite.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, follow_redirects=True)
        html = resp.text
        soup = BeautifulSoup(html, "html.parser")

        # Try to extract case details
        case_info = {
            "url": url,
            "title": "",
            "court": "",
            "parties": [],
            "attorneys": [],
            "docket_entries": [],
        }

        # Try to find title
        title_selectors = ["h1", "h2", "title", ".case-title", ".title"]
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                case_info["title"] = title_elem.get_text(strip=True)
                break

        # Try to find court
        court_selectors = [".court", "[class*='court']", "p:contains('Court')"]
        for selector in court_selectors:
            court_elem = soup.select_one(selector)
            if court_elem:
                text = court_elem.get_text(strip=True)
                if "court" in text.lower():
                    case_info["court"] = text
                    break

        # Try to find parties
        party_selectors = [".parties", "[class*='party']", "div:contains('Plaintiff')"]
        for selector in party_selectors:
            party_elems = soup.select(selector)
            if party_elems:
                for elem in party_elems:
                    text = elem.get_text(strip=True)
                    if text:
                        case_info["parties"].append(text)

        # Try to find attorneys
        attorney_selectors = [".attorney", "[class*='attorney']", "div:contains('Attorney')"]
        for selector in attorney_selectors:
            atty_elems = soup.select(selector)
            if atty_elems:
                for elem in atty_elems:
                    text = elem.get_text(strip=True)
                    if text:
                        case_info["attorneys"].append(text)

        return case_info
