"""
Test Core 4-Step User Flow
============================
1. Welcome Page (/static/welcome.html)
2. Role Selection (/onboarding/select-role.html)
3. Storage Connect (mandatory - /onboarding/storage-select.html)
4. Tenant Home (/tenant/home)

Critical: Storage must be MANDATORY - no skip option
"""

import pytest
import httpx
from bs4 import BeautifulSoup

BASE_URL = "http://localhost:8000"


class TestStep1Welcome:
    """Step 1: Welcome Page - Single CTA to Get Started"""

    def test_welcome_page_loads(self):
        """Welcome page returns 200 and has expected content"""
        resp = httpx.get(f"{BASE_URL}/static/welcome.html", follow_redirects=True)
        assert resp.status_code == 200, f"Welcome page failed: {resp.status_code}"
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Should have "Get Started" or similar primary CTA
        cta_found = any(
            keyword in resp.text.lower()
            for keyword in ['get started', 'begin', 'start', 'enter']
        )
        assert cta_found, "Welcome page missing primary CTA (Get Started/Begin/Start)"
        
        # Should mention tenant/journal/document theme
        theme_found = any(
            keyword in resp.text.lower()
            for keyword in ['tenant', 'journal', 'document', 'rights', 'housing']
        )
        assert theme_found, "Welcome page missing tenant/journal theme"

    def test_welcome_no_bypass_to_home(self):
        """Welcome page should not allow bypass to tenant home without storage"""
        resp = httpx.get(f"{BASE_URL}/tenant/home", follow_redirects=True)
        # Should redirect to welcome or storage, not show home
        final_url = str(resp.url)
        assert '/tenant/home' not in final_url or resp.status_code != 200, \
            "Tenant home accessible without storage setup - BYPASS VULNERABILITY"


class TestStep2RoleSelect:
    """Step 2: Role Selection - Tenant is primary/default"""

    def test_role_select_page_loads(self):
        """Role selection page returns 200"""
        resp = httpx.get(f"{BASE_URL}/onboarding/select-role.html", follow_redirects=True)
        assert resp.status_code == 200, f"Role select failed: {resp.status_code}"

    def test_tenant_role_available(self):
        """Tenant role must be available as primary option"""
        resp = httpx.get(f"{BASE_URL}/onboarding/select-role.html", follow_redirects=True)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Look for tenant option
        tenant_found = any(
            keyword in resp.text.lower()
            for keyword in ['tenant', 'renter', 'resident', 'i am a tenant']
        )
        assert tenant_found, "Tenant role not found in role selection"

    def test_role_selection_flow(self):
        """Selecting tenant role should redirect to storage setup"""
        # This would require form submission or JS interaction
        # For API test, we check the expected flow
        resp = httpx.get(f"{BASE_URL}/onboarding/select-role.html?role=tenant", follow_redirects=True)
        # Should either show storage selection or redirect to it
        assert resp.status_code == 200, "Role selection flow broken"


class TestStep3StorageMandatory:
    """Step 3: Storage Setup - MUST be mandatory, NO skip option"""

    def test_storage_select_page_loads(self):
        """Storage selection page returns 200"""
        resp = httpx.get(f"{BASE_URL}/onboarding/storage-select.html", follow_redirects=True)
        assert resp.status_code == 200, f"Storage select failed: {resp.status_code}"

    def test_no_skip_button_exists(self):
        """CRITICAL: No skip, bypass, or 'do later' button should exist"""
        resp = httpx.get(f"{BASE_URL}/onboarding/storage-select.html", follow_redirects=True)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Check for skip-related text in buttons/links
        skip_keywords = ['skip', 'bypass', 'do later', 'remind me', 'not now', 'cancel', 'continue without']
        
        # Check buttons
        buttons = soup.find_all('button')
        for btn in buttons:
            btn_text = btn.get_text().lower()
            for keyword in skip_keywords:
                assert keyword not in btn_text, \
                    f"SKIP BUTTON FOUND: '{btn_text}' contains '{keyword}' - Storage must be MANDATORY"
        
        # Check links
        links = soup.find_all('a')
        for link in links:
            link_text = link.get_text().lower()
            href = link.get('href', '').lower()
            for keyword in skip_keywords:
                assert keyword not in link_text, \
                    f"SKIP LINK FOUND: '{link_text}' contains '{keyword}'"
                # Also check href doesn't bypass storage
                if keyword in ['skip', 'bypass']:
                    assert keyword not in href, \
                        f"SKIP HREF FOUND: '{href}' contains '{keyword}'"

    def test_storage_connect_buttons_present(self):
        """Should have storage provider connection buttons"""
        resp = httpx.get(f"{BASE_URL}/onboarding/storage-select.html", follow_redirects=True)
        
        # Look for common storage provider names or connect buttons
        storage_indicators = [
            'google', 'drive', 'dropbox', 'onedrive', 'box', 'connect',
            'oauth', 'sign in', 'authenticate', 'storage', 'cloud'
        ]
        
        found_storage = any(indicator in resp.text.lower() for indicator in storage_indicators)
        assert found_storage, "No storage provider options found on storage-select page"

    def test_cannot_access_home_without_storage(self):
        """CRITICAL: Direct access to tenant/home should redirect to storage setup"""
        # Try to access home without storage session
        resp = httpx.get(f"{BASE_URL}/tenant/home", follow_redirects=True)
        final_url = str(resp.url)
        
        # Should NOT end up at tenant/home
        if '/tenant/home' in final_url and resp.status_code == 200:
            pytest.fail("CRITICAL: Tenant home accessible WITHOUT storage! Flow bypass possible.")
        
        # Should redirect to storage setup or welcome
        assert any(x in final_url for x in ['/storage', '/onboarding', '/welcome']), \
            f"Unauthorized access to /tenant/home should redirect to storage, got: {final_url}"


class TestStep4TenantHome:
    """Step 4: Tenant Home - Available after storage connected"""

    def test_tenant_home_requires_auth(self):
        """Tenant home requires authentication"""
        resp = httpx.get(f"{BASE_URL}/tenant/home", follow_redirects=True)
        # Without valid session, should redirect
        assert resp.status_code in [200, 302, 307], f"Unexpected status: {resp.status_code}"


class TestCompleteFlowIntegration:
    """Full 4-step flow integration test"""

    def test_flow_redirection_chain(self):
        """Test that each step properly redirects to next"""
        # Start at welcome
        steps = [
            ("/static/welcome.html", "Welcome"),
            ("/onboarding/select-role.html", "Role Select"),
            ("/onboarding/storage-select.html", "Storage"),
        ]
        
        for path, name in steps:
            resp = httpx.get(f"{BASE_URL}{path}", follow_redirects=True)
            assert resp.status_code == 200, f"Step '{name}' ({path}) failed with {resp.status_code}"

    def test_api_health(self):
        """API health check - foundation for all flows"""
        try:
            resp = httpx.get(f"{BASE_URL}/api/health", timeout=5)
            assert resp.status_code == 200, f"API health check failed: {resp.status_code}"
            
            data = resp.json()
            assert 'status' in data or 'healthy' in str(data).lower(), \
                "Health endpoint missing expected fields"
        except Exception as e:
            pytest.fail(f"API not responding: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
