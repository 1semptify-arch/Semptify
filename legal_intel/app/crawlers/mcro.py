# app/crawlers/mcro.py
from datetime import datetime

from playwright.async_api import async_playwright

MCRO_SEARCH_URL = "https://publicaccess.courts.state.mn.us/CaseSearch"


async def fetch_cases_by_attorney(bar_number: str) -> list[dict]:
    """
    Fetch cases for an attorney by bar number from MCRO.

    MCRO uses ASP.NET WebForms with tab-based navigation.
    The attorney search is typically on the "Case Search" tab.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto(MCRO_SEARCH_URL, wait_until="networkidle")

            # Wait for the page to fully load
            await page.wait_for_selector("body", timeout=10000)

            # MCRO has tabs - look for attorney search tab or input
            # Common selectors for attorney bar number input in ASP.NET apps
            attorney_input_selectors = [
                "input[name*='Attorney']",
                "input[id*='Attorney']",
                "input[placeholder*='Attorney']",
                "input[placeholder*='Bar']",
                "#ctl00_ContentPlaceHolder1_AttorneyNumber",
                "#txtAttorneyNumber",
            ]

            attorney_input = None
            for selector in attorney_input_selectors:
                try:
                    attorney_input = await page.query_selector(selector)
                    if attorney_input:
                        break
                except Exception:
                    continue

            if not attorney_input:
                # Try to find by label text
                attorney_input = await page.query_selector(
                    "xpath=//label[contains(text(), 'Attorney')]/following-sibling::input"
                )

            if not attorney_input:
                raise ValueError("Could not find attorney bar number input field")

            await attorney_input.fill(bar_number)

            # Find and click search button
            search_button_selectors = [
                "input[type='submit'][value*='Search']",
                "button[type='submit']",
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

            # Wait for results to load
            await page.wait_for_load_state("networkidle", timeout=15000)
            await page.wait_for_timeout(2000)

            # Look for results table - MCRO typically uses GridView or similar
            results_table_selectors = [
                "table[id*='GridView']",
                "table[id*='Results']",
                "table.case-results",
                "table.search-results",
                ".grid-view",
            ]

            results_table = None
            for selector in results_table_selectors:
                try:
                    results_table = await page.query_selector(selector)
                    if results_table:
                        break
                except Exception:
                    continue

            if not results_table:
                # Try to find any table with rows
                tables = await page.query_selector_all("table")
                for table in tables:
                    rows = await table.query_selector_all("tr")
                    if len(rows) > 1:  # Has header + data
                        results_table = table
                        break

            if not results_table:
                return []

            rows = await results_table.query_selector_all("tr")
            cases: list[dict] = []

            # Skip header row if present
            data_rows = rows[1:] if len(rows) > 1 else rows

            for row in data_rows:
                try:
                    cells = await row.query_selector_all("td")
                    if len(cells) < 2:
                        continue

                    # Try to extract case data from cells
                    # Typical MCRO results: Case Number, Case Title, Court, Case Type, Filing Date, Status
                    case_number = (await cells[0].inner_text()).strip() if len(cells) > 0 else ""
                    case_title = (await cells[1].inner_text()).strip() if len(cells) > 1 else ""
                    court = (await cells[2].inner_text()).strip() if len(cells) > 2 else ""
                    case_type = (await cells[3].inner_text()).strip() if len(cells) > 3 else ""
                    filing_date = (await cells[4].inner_text()).strip() if len(cells) > 4 else None
                    status = (await cells[5].inner_text()).strip() if len(cells) > 5 else ""

                    # Check for case detail link
                    case_link = await cells[0].query_selector("a")
                    case_id = None
                    if case_link:
                        href = await case_link.get_attribute("href")
                        if href:
                            # Extract case ID from URL
                            if "CaseID=" in href:
                                case_id = href.split("CaseID=")[1].split("&")[0]

                    if case_number:
                        cases.append(
                            {
                                "case_number": case_number,
                                "case_title": case_title,
                                "court": court,
                                "case_type": case_type,
                                "filing_date": filing_date,
                                "status": status,
                                "case_id": case_id,
                            }
                        )
                except Exception:
                    # Skip problematic rows
                    continue

            return cases

        finally:
            await browser.close()


async def fetch_case_docket(case_detail_url: str) -> list[dict]:
    """
    Fetch docket entries for a case from MCRO.

    The docket is typically on the case detail page under a "Register of Actions" tab.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto(case_detail_url, wait_until="networkidle")
            await page.wait_for_timeout(2000)

            # Look for Register of Actions tab or section
            roa_tab_selectors = [
                "a:has-text('Register of Actions')",
                "a:has-text('ROA')",
                "input[id*='ROA']",
                "#ctl00_ContentPlaceHolder1_TabROA",
            ]

            roa_tab = None
            for selector in roa_tab_selectors:
                try:
                    roa_tab = await page.query_selector(selector)
                    if roa_tab:
                        break
                except Exception:
                    continue

            if roa_tab:
                await roa_tab.click()
                await page.wait_for_timeout(2000)

            # Look for docket table
            docket_table_selectors = [
                "table[id*='ROA']",
                "table[id*='Docket']",
                "table[id*='Register']",
                "table.roa-table",
                "table.docket-table",
            ]

            docket_table = None
            for selector in docket_table_selectors:
                try:
                    docket_table = await page.query_selector(selector)
                    if docket_table:
                        break
                except Exception:
                    continue

            if not docket_table:
                # Try to find any table that looks like a docket
                tables = await page.query_selector_all("table")
                for table in tables:
                    rows = await table.query_selector_all("tr")
                    if len(rows) > 1:
                        # Check if first row has date-like content
                        first_cell = await rows[0].query_selector("td")
                        if first_cell:
                            text = await first_cell.inner_text()
                            if any(char.isdigit() for char in text):
                                docket_table = table
                                break

            if not docket_table:
                return []

            rows = await docket_table.query_selector_all("tr")
            dockets: list[dict] = []

            # Skip header row
            data_rows = rows[1:] if len(rows) > 1 else rows

            for row in data_rows:
                try:
                    cells = await row.query_selector_all("td")
                    if len(cells) < 2:
                        continue

                    # Typical docket: Date, Entry Type, Description, Document Link
                    date_str = (await cells[0].inner_text()).strip() if len(cells) > 0 else ""
                    entry_type = (await cells[1].inner_text()).strip() if len(cells) > 1 else ""
                    description = (await cells[2].inner_text()).strip() if len(cells) > 2 else ""

                    # Parse date
                    parsed_date = None
                    if date_str:
                        try:
                            # Try common date formats
                            for fmt in ["%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y", "%d-%b-%Y"]:
                                try:
                                    parsed_date = datetime.strptime(date_str, fmt).date()
                                    break
                                except Exception:
                                    continue
                        except Exception:
                            pass

                    # Check for document link
                    document_url = None
                    if len(cells) > 3:
                        doc_link = await cells[3].query_selector("a")
                        if doc_link:
                            document_url = await doc_link.get_attribute("href")

                    dockets.append(
                        {
                            "date": parsed_date,
                            "date_str": date_str,
                            "entry_type": entry_type,
                            "description": description,
                            "document_url": document_url,
                        }
                    )
                except Exception:
                    continue

            return dockets

        finally:
            await browser.close()
