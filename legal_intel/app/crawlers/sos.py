# app/crawlers/sos.py
from playwright.async_api import async_playwright
from typing import Dict, Optional

MN_SOS_SEARCH_URL = "https://mblsportal.sos.mn.gov/Business/Search"
ND_SOS_SEARCH_URL = "https://firststop.sos.nd.gov/search/business"

async def fetch_entity_from_sos(name: str, state: str = "MN") -> Optional[Dict]:
    """
    Fetch entity information from Secretary of State business search.
    
    Supports MN and ND SOS portals.
    """
    if state == "MN":
        return await fetch_mn_sos_entity(name)
    elif state == "ND":
        return await fetch_nd_sos_entity(name)
    else:
        return None

async def fetch_mn_sos_entity(name: str) -> Optional[Dict]:
    """
    Fetch entity from Minnesota Secretary of State Business & Liens Portal.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        try:
            await page.goto(MN_SOS_SEARCH_URL, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)

            # MN SOS portal uses input[name='BusinessName'] as the primary search field
            search_input_selectors = [
                "input[name='BusinessName']",
                "input[name='search-box']",
                "input[name='search']",
                "input[id*='search']",
                "input[placeholder*='Business']",
                "input[placeholder*='Search']",
                "#txtSearch",
                "input[type='text']",
            ]

            search_input = None
            for selector in search_input_selectors:
                try:
                    search_input = await page.query_selector(selector)
                    if search_input:
                        break
                except Exception:
                    continue

            if not search_input:
                raise ValueError("Could not find search input field")
            
            await search_input.fill(name)
            
            # Find and click search button
            search_button_selectors = [
                "input[type='submit'][value*='Search']",
                "button[type='submit']",
                "button:has-text('Search')",
                "input[id*='Search']",
                "input[id*='Submit']",
                "#btnSearch",
                "#ctl00_ContentPlaceHolder1_btnSearch",
            ]
            
            search_button = None
            for selector in search_button_selectors:
                try:
                    search_button = await page.query_selector(selector)
                    if search_button:
                        break
                except Exception:
                    continue
            
            if not search_button:
                raise ValueError("Could not find search button")
            
            await search_button.click()
            
            # Wait for results
            await page.wait_for_load_state("networkidle", timeout=15000)
            await page.wait_for_timeout(2000)
            
            # Look for results table or grid
            results_selectors = [
                "table[id*='Results']",
                "table[id*='GridView']",
                "table.search-results",
                "table.business-results",
                ".results-table",
                ".grid-view",
            ]
            
            results_container = None
            for selector in results_selectors:
                try:
                    results_container = await page.query_selector(selector)
                    if results_container:
                        break
                except Exception:
                    continue
            
            if not results_container:
                # Try to find any table with rows
                tables = await page.query_selector_all("table")
                for table in tables:
                    rows = await table.query_selector_all("tr")
                    if len(rows) > 1:
                        results_container = table
                        break
            
            if not results_container:
                return None
            
            rows = await results_container.query_selector_all("tr")

            # Skip header row
            data_rows = rows[1:] if len(rows) > 1 else rows

            if not data_rows:
                return None

            # MN SOS new layout: first cell contains all entity info as labeled text
            first_row = data_rows[0]
            cells = await first_row.query_selector_all("td")

            if not cells:
                return None

            cell_text = (await cells[0].inner_text()).strip()

            # Parse the multi-line cell: "Entity Name\nBusiness Status:\nBusiness Type:\nName Type:\nActive\nLLC\n..."
            lines = [ln.strip() for ln in cell_text.splitlines() if ln.strip()]

            entity_name = lines[0] if lines else ""
            entity_type = ""
            status = ""

            # MN SOS layout: ALL labels come first, then ALL values in the same order
            # e.g. lines = ["Name", "Business Status:", "Business Type:", "Name Type:", "Active", "LLC (Domestic)", "MN Business Name"]
            label_lines = [l for l in lines[1:] if l.endswith(":")]
            value_lines = [l for l in lines[1:] if not l.endswith(":")]

            label_map = {}
            for label, value in zip(label_lines, value_lines):
                label_map[label.rstrip(":")] = value

            entity_type = label_map.get("Business Type", "")
            status = label_map.get("Business Status", "")

            # Click Details link to get registered agent and address
            detail_link = await first_row.query_selector("a")
            if detail_link:
                await detail_link.click()
                await page.wait_for_load_state("domcontentloaded", timeout=15000)
                await page.wait_for_timeout(2000)

                registered_agent = await extract_field(page, ["Registered Agent", "Agent"])
                address = await extract_field(page, ["Address", "Registered Office", "Principal Office"])
                filing_date = await extract_field(page, ["Filing Date", "Date Filed"])
                # Status from detail page (overrides if found)
                detail_status = await extract_field(page, ["Status", "Business Status"])
                if detail_status:
                    status = detail_status
            else:
                registered_agent = ""
                address = ""
                filing_date = None

            return {
                "name": entity_name,
                "type": entity_type,
                "sos_id": "",
                "registered_agent": registered_agent,
                "address": address,
                "filing_date": filing_date,
                "status": status,
            }
            
        finally:
            await browser.close()

async def fetch_nd_sos_entity(name: str) -> Optional[Dict]:
    """
    Fetch entity from North Dakota Secretary of State FirstStop portal.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            await page.goto(ND_SOS_SEARCH_URL, wait_until="networkidle")
            await page.wait_for_timeout(2000)
            
            # ND SOS search input
            search_input_selectors = [
                "input[name='search']",
                "input[id*='search']",
                "input[placeholder*='Business']",
                "input[placeholder*='Search']",
                "#search",
                "input[type='text']",
            ]
            
            search_input = None
            for selector in search_input_selectors:
                try:
                    search_input = await page.query_selector(selector)
                    if search_input:
                        break
                except Exception:
                    continue
            
            if not search_input:
                raise ValueError("Could not find search input field")
            
            await search_input.fill(name)
            
            # Find and click search button
            search_button_selectors = [
                "button[type='submit']",
                "button:has-text('Search')",
                "input[type='submit']",
                "#search-button",
            ]
            
            search_button = None
            for selector in search_button_selectors:
                try:
                    search_button = await page.query_selector(selector)
                    if search_button:
                        break
                except Exception:
                    continue
            
            if not search_button:
                raise ValueError("Could not find search button")
            
            await search_button.click()
            
            # Wait for results
            await page.wait_for_load_state("networkidle", timeout=15000)
            await page.wait_for_timeout(2000)
            
            # Look for results
            results_selectors = [
                "table.results",
                "table.search-results",
                ".business-results",
                ".results-list",
            ]
            
            results_container = None
            for selector in results_selectors:
                try:
                    results_container = await page.query_selector(selector)
                    if results_container:
                        break
                except Exception:
                    continue
            
            if not results_container:
                # Try to find any table with rows
                tables = await page.query_selector_all("table")
                for table in tables:
                    rows = await table.query_selector_all("tr")
                    if len(rows) > 1:
                        results_container = table
                        break
            
            if not results_container:
                return None
            
            rows = await results_container.query_selector_all("tr")
            data_rows = rows[1:] if len(rows) > 1 else rows
            
            if not data_rows:
                return None
            
            first_row = data_rows[0]
            cells = await first_row.query_selector_all("td")
            
            if len(cells) < 2:
                return None
            
            entity_name = (await cells[0].inner_text()).strip() if len(cells) > 0 else ""
            entity_type = (await cells[1].inner_text()).strip() if len(cells) > 1 else ""
            sos_id = (await cells[2].inner_text()).strip() if len(cells) > 2 else ""
            
            # Click into detail page
            detail_link = await cells[0].query_selector("a")
            if detail_link:
                await detail_link.click()
                await page.wait_for_load_state("networkidle", timeout=15000)
                await page.wait_for_timeout(2000)
                
                registered_agent = await extract_field(page, ["Registered Agent", "Agent"])
                address = await extract_field(page, ["Address", "Registered Office"])
                filing_date = await extract_field(page, ["Filing Date", "Date Filed"])
                status = await extract_field(page, ["Status", "Business Status"])
            else:
                registered_agent = ""
                address = ""
                filing_date = None
                status = ""
            
            return {
                "name": entity_name,
                "type": entity_type,
                "sos_id": sos_id,
                "registered_agent": registered_agent,
                "address": address,
                "filing_date": filing_date,
                "status": status,
            }
            
        finally:
            await browser.close()

async def extract_field(page, field_labels: list) -> str:
    """
    Extract a field value from a detail page by looking for label text.
    Handles DT/DD definition lists (MN SOS), table rows, and div pairs.
    """
    for label in field_labels:
        try:
            # Strategy 1: DT/DD definition list (MN SOS uses this)
            value = await page.evaluate(
                """(label) => {
                    const dts = document.querySelectorAll('dt');
                    for (let dt of dts) {
                        if (dt.textContent.trim().toLowerCase().includes(label.toLowerCase())) {
                            const dd = dt.nextElementSibling;
                            if (dd && dd.tagName === 'DD') {
                                return dd.textContent.trim();
                            }
                        }
                    }
                    return null;
                }""",
                label
            )
            if value:
                return value

            # Strategy 2: table row - label in first cell, value in next cell
            value = await page.evaluate(
                """(label) => {
                    const tds = document.querySelectorAll('td, th');
                    for (let td of tds) {
                        if (td.textContent.trim().toLowerCase().includes(label.toLowerCase())) {
                            const next = td.nextElementSibling;
                            if (next) return next.textContent.trim();
                        }
                    }
                    return null;
                }""",
                label
            )
            if value:
                return value

            # Strategy 3: any element whose text matches, get the next sibling
            label_element = await page.query_selector(f"text={label}")
            if label_element:
                value = await page.evaluate(
                    "el => el.nextElementSibling ? el.nextElementSibling.textContent.trim() : ''",
                    label_element
                )
                if value:
                    return value

        except Exception:
            continue

    return ""
