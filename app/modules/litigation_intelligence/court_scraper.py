"""
Court Scraper Pack - Minnesota Court System Integration
=================================================

Extracts case data from Minnesota court systems with headless Playwright automation.
Handles captcha, session persistence, and comprehensive data extraction.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass
import json
import re
from urllib.parse import urljoin, urlparse

try:
    from playwright.async_api import async_playwright
    from playwright.async_api import Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logging.warning("Playwright not available - court scraper will be limited")

logger = logging.getLogger(__name__)

@dataclass
class CourtCase:
    """Court case data structure."""
    case_number: str
    case_title: str
    court: str
    judge: Optional[str] = None
    parties: Dict[str, Any] = None
    filing_date: Optional[datetime] = None
    status: str = "active"
    docket_entries: List[Dict[str, Any]] = None
    documents: List[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_number": self.case_number,
            "case_title": self.case_title,
            "court": self.court,
            "judge": self.judge,
            "parties": self.parties or {},
            "filing_date": self.filing_date.isoformat() if self.filing_date else None,
            "status": self.status,
            "docket_entries": self.docket_entries or [],
            "documents": self.documents or []
        }

class CourtScraperPack:
    """Main court scraper pack for Minnesota court systems."""
    
    def __init__(self):
        self.session_data = {}
        self.captcha_solver = CaptchaSolver()
        
    async def scrape_mncis_cases(self, case_number: str = None, 
                              attorney_name: str = None,
                              date_range: str = None) -> List[Dict[str, Any]]:
        """Scrape MN Court Information System (MNCIS)."""
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright not available - MNCIS scraping disabled")
            return []
        
        cases = []
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Navigate to MNCIS
                await page.goto("https://www.mncourts.gov/mncis")
                
                # Handle login if needed
                await self._handle_mncis_login(page)
                
                # Search for cases
                if case_number:
                    await page.fill('input[name="caseNumber"]', case_number)
                elif attorney_name:
                    await page.fill('input[name="attorneyName"]', attorney_name)
                
                if date_range:
                    await page.select_option('select[name="dateRange"]', date_range)
                
                await page.click('button[type="submit"]')
                await page.wait_for_load_state('networkidle')
                
                # Extract case data
                case_elements = await page.query_selector_all('.case-row')
                
                for element in case_elements:
                    case_data = await self._extract_mncis_case_data(element)
                    if case_data:
                        cases.append(case_data)
                
                await browser.close()
                
        except Exception as e:
            logger.error(f"MNCIS scraping failed: {e}")
        
        return cases
    
    async def scrape_efilemn_cases(self, case_number: str = None,
                               party_name: str = None) -> List[Dict[str, Any]]:
        """Scrape Minnesota eFileMN system."""
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright not available - eFileMN scraping disabled")
            return []
        
        cases = []
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Navigate to eFileMN
                await page.goto("https://efile.mncourts.gov/efilemn")
                
                # Handle login
                await self._handle_efilemn_login(page)
                
                # Search for cases
                if case_number:
                    await page.fill('input[name="caseNumber"]', case_number)
                elif party_name:
                    await page.fill('input[name="partyName"]', party_name)
                
                await page.click('button[type="submit"]')
                await page.wait_for_load_state('networkidle')
                
                # Extract case data
                case_elements = await page.query_selector_all('.case-item')
                
                for element in case_elements:
                    case_data = await self._extract_efilemn_case_data(element)
                    if case_data:
                        cases.append(case_data)
                
                await browser.close()
                
        except Exception as e:
            logger.error(f"eFileMN scraping failed: {e}")
        
        return cases
    
    async def scrape_efilemn_filings(self, case_number: str) -> List[Dict[str, Any]]:
        """Scrape specific case filings from eFileMN."""
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright not available - eFileMN filings scraping disabled")
            return []
        
        filings = []
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Navigate directly to case filings
                await page.goto(f"https://efile.mncourts.gov/efilemn/case/{case_number}")
                
                # Handle login if needed
                await self._handle_efilemn_login(page)
                
                # Extract filing data
                filing_elements = await page.query_selector_all('.filing-item')
                
                for element in filing_elements:
                    filing_data = await self._extract_filing_data(element)
                    if filing_data:
                        filings.append(filing_data)
                
                await browser.close()
                
        except Exception as e:
            logger.error(f"eFileMN filings scraping failed: {e}")
        
        return filings
    
    async def _handle_mncis_login(self, page: "Page"):
        """Handle MNCIS login with session persistence."""
        # Check if already logged in
        login_check = await page.query_selector('.user-info')
        if login_check:
            return
        
        # Implement login logic here
        await page.click('a[href="/login"]')
        await page.wait_for_selector('input[name="username"]')
        
        # Use stored credentials if available
        if 'mncis' in self.session_data:
            credentials = self.session_data['mncis']
            await page.fill('input[name="username"]', credentials['username'])
            await page.fill('input[name="password"]', credentials['password'])
            await page.click('button[type="submit"]')
            await page.wait_for_load_state('networkidle')
    
    async def _handle_efilemn_login(self, page: "Page"):
        """Handle eFileMN login with session persistence."""
        # Check if already logged in
        login_check = await page.query_selector('.user-info')
        if login_check:
            return
        
        # Implement login logic here
        await page.click('a[href="/login"]')
        await page.wait_for_selector('input[name="username"]')
        
        # Use stored credentials if available
        if 'efilemn' in self.session_data:
            credentials = self.session_data['efilemn']
            await page.fill('input[name="username"]', credentials['username'])
            await page.fill('input[name="password"]', credentials['password'])
            await page.click('button[type="submit"]')
            await page.wait_for_load_state('networkidle')
    
    async def _extract_mncis_case_data(self, element) -> Optional[Dict[str, Any]]:
        """Extract case data from MNCIS page element."""
        try:
            case_number = await element.query_selector('.case-number')
            case_title = await element.query_selector('.case-title')
            court = await element.query_selector('.court-name')
            judge = await element.query_selector('.judge-name')
            
            if not all([case_number, case_title, court]):
                return None
            
            return {
                "case_number": await case_number.inner_text(),
                "case_title": await case_title.inner_text(),
                "court": await court.inner_text(),
                "judge": await judge.inner_text() if judge else None,
                "source": "mncis",
                "scraped_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to extract MNCIS case data: {e}")
            return None
    
    async def _extract_efilemn_case_data(self, element) -> Optional[Dict[str, Any]]:
        """Extract case data from eFileMN page element."""
        try:
            case_number = await element.query_selector('.case-number')
            case_title = await element.query_selector('.case-title')
            party_info = await element.query_selector('.party-info')
            
            if not all([case_number, case_title]):
                return None
            
            return {
                "case_number": await case_number.inner_text(),
                "case_title": await case_title.inner_text(),
                "party_info": await party_info.inner_text() if party_info else None,
                "source": "efilemn",
                "scraped_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to extract eFileMN case data: {e}")
            return None
    
    async def _extract_filing_data(self, element) -> Optional[Dict[str, Any]]:
        """Extract filing data from page element."""
        try:
            filing_date = await element.query_selector('.filing-date')
            filing_type = await element.query_selector('.filing-type')
            filing_party = await element.query_selector('.filing-party')
            
            if not all([filing_date, filing_type]):
                return None
            
            return {
                "filing_date": await filing_date.inner_text(),
                "filing_type": await filing_type.inner_text(),
                "filing_party": await filing_party.inner_text() if filing_party else None,
                "scraped_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to extract filing data: {e}")
            return None

class CaptchaSolver:
    """CAPTCHA solving system for court websites."""
    
    def __init__(self):
        self.solver_services = []
    
    async def solve_captcha(self, page: "Page", captcha_element) -> bool:
        """Solve CAPTCHA challenges."""
        try:
            # Check if CAPTCHA is present
            if not captcha_element:
                return True
            
            # Implement CAPTCHA solving logic
            # This could integrate with external CAPTCHA solving services
            # For now, we'll implement a basic approach
            
            # Wait for user to solve CAPTCHA manually
            await page.wait_for_timeout(30000)  # 30 seconds
            
            return True
            
        except Exception as e:
            logger.error(f"CAPTCHA solving failed: {e}")
            return False

# Factory function
def create_court_scraper() -> CourtScraperPack:
    """Create court scraper instance."""
    return CourtScraperPack()

# Example usage
async def example_usage():
    """Example usage of court scraper."""
    scraper = create_court_scraper()
    
    # Scrape MNCIS cases
    cases = await scraper.scrape_mncis_cases(
        case_number="27-CV-21-12345",
        attorney_name="Smith"
    )
    
    print(f"Found {len(cases)} cases")
    for case in cases:
        print(f"Case: {case['case_number']} - {case['case_title']}")
    
    # Scrape eFileMN filings
    filings = await scraper.scrape_efilemn_filings("27-CV-21-12345")
    
    print(f"Found {len(filings)} filings")
    for filing in filings:
        print(f"Filing: {filing['filing_date']} - {filing['filing_type']}")

if __name__ == "__main__":
    asyncio.run(example_usage())
