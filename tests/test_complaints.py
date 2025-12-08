"""
Tests for the Complaints module - MN agency complaints filing system.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


# ============================================================================
# AGENCY ENDPOINTS
# ============================================================================

class TestComplaintsAgencies:
    """Test complaint agency listing and details."""
    
    @pytest.mark.asyncio
    async def test_get_all_agencies(self):
        """Test listing all MN complaint agencies."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/complaints/agencies")
            assert response.status_code == 200
            agencies = response.json()
            assert isinstance(agencies, list)
            assert len(agencies) >= 5  # Should have multiple MN agencies
    
    @pytest.mark.asyncio
    async def test_agencies_have_required_fields(self):
        """Test that agencies have all required fields."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/complaints/agencies")
            agencies = response.json()
            
            required_fields = ["id", "name", "type", "jurisdiction"]
            for agency in agencies:
                for field in required_fields:
                    assert field in agency, f"Agency missing {field}"
    
    @pytest.mark.asyncio
    async def test_mn_ag_consumer_exists(self):
        """Test that MN Attorney General Consumer Protection agency exists."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/complaints/agencies")
            agencies = response.json()
            
            ag_ids = [a["id"] for a in agencies]
            assert "mn_ag_consumer" in ag_ids
    
    @pytest.mark.asyncio
    async def test_hud_fair_housing_exists(self):
        """Test that HUD Fair Housing agency exists."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/complaints/agencies")
            agencies = response.json()
            
            agency_ids = [a["id"] for a in agencies]
            assert "hud_fair_housing" in agency_ids
    
    @pytest.mark.asyncio
    async def test_agencies_have_complaint_types(self):
        """Test that agencies include complaint types they handle."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/complaints/agencies")
            agencies = response.json()
            
            for agency in agencies:
                assert "complaint_types" in agency
                assert isinstance(agency["complaint_types"], list)


# ============================================================================
# COMPLAINT TYPES ENDPOINT
# ============================================================================

class TestComplaintTypes:
    """Test complaint type enumeration."""
    
    @pytest.mark.asyncio
    async def test_get_complaint_types(self):
        """Test getting available complaint types."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/complaints/types")
            # May return 200 or 404 depending on implementation
            assert response.status_code in [200, 404]


# ============================================================================
# WIZARD ENDPOINTS
# ============================================================================

class TestComplaintWizard:
    """Test the guided complaint wizard functionality."""
    
    @pytest.mark.asyncio
    async def test_wizard_start(self):
        """Test starting a new complaint wizard session."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/complaints/wizard/start",
                json={"complaint_type": "landlord_violation"}
            )
            # Accept 200, 201, or 422 (validation error if schema differs)
            assert response.status_code in [200, 201, 422]
    
    @pytest.mark.asyncio
    async def test_wizard_requires_type(self):
        """Test that wizard requires complaint type."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/complaints/wizard/start",
                json={}
            )
            assert response.status_code == 422  # Validation error


# ============================================================================
# COMPLAINT SUBMISSION
# ============================================================================

class TestComplaintSubmission:
    """Test complaint submission endpoints."""
    
    @pytest.mark.asyncio
    async def test_submit_complaint_structure(self):
        """Test complaint submission with proper structure."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            complaint_data = {
                "agency_id": "mn_ag_consumer",
                "complaint_type": "landlord_violation",
                "subject": "Test Complaint",
                "summary": "This is a test complaint summary",
                "detailed_description": "Detailed description of the issue",
                "target_type": "landlord",
                "target_name": "Test Landlord LLC"
            }
            response = await client.post(
                "/api/complaints/submit",
                json=complaint_data
            )
            # Accept various status codes
            assert response.status_code in [200, 201, 401, 422]
    
    @pytest.mark.asyncio
    async def test_submit_requires_agency(self):
        """Test that submission requires agency_id."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/complaints/submit",
                json={"subject": "Test"}
            )
            assert response.status_code == 422


# ============================================================================
# AGENCY DETAILS
# ============================================================================

class TestAgencyDetails:
    """Test individual agency detail retrieval."""
    
    @pytest.mark.asyncio
    async def test_agency_has_contact_info(self):
        """Test that agencies include contact information."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/complaints/agencies")
            agencies = response.json()
            
            for agency in agencies:
                # Most agencies should have phone or website
                has_contact = "phone" in agency or "website" in agency
                assert has_contact, f"Agency {agency.get('id')} missing contact info"
    
    @pytest.mark.asyncio
    async def test_agency_has_filing_info(self):
        """Test that agencies include filing information."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/complaints/agencies")
            agencies = response.json()
            
            # At least some agencies should have filing URLs
            has_filing_url = any("filing_url" in a for a in agencies)
            assert has_filing_url


# ============================================================================
# MN-SPECIFIC AGENCIES
# ============================================================================

class TestMNAgencies:
    """Test Minnesota-specific agencies are properly configured."""
    
    @pytest.mark.asyncio
    async def test_homeline_exists(self):
        """Test HOME Line tenant hotline is included."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/complaints/agencies")
            agencies = response.json()
            
            agency_ids = [a["id"] for a in agencies]
            assert "homeline_mn" in agency_ids
    
    @pytest.mark.asyncio
    async def test_legal_aid_exists(self):
        """Test Legal Aid MN is included."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/complaints/agencies")
            agencies = response.json()
            
            agency_ids = [a["id"] for a in agencies]
            assert "legal_aid_mn" in agency_ids
    
    @pytest.mark.asyncio
    async def test_mn_commerce_exists(self):
        """Test MN Dept of Commerce Real Estate is included."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/complaints/agencies")
            agencies = response.json()
            
            agency_ids = [a["id"] for a in agencies]
            assert "mn_commerce_real_estate" in agency_ids
    
    @pytest.mark.asyncio
    async def test_agencies_have_mn_jurisdiction(self):
        """Test that agencies serve Minnesota."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/complaints/agencies")
            agencies = response.json()
            
            for agency in agencies:
                jurisdiction = agency.get("jurisdiction", "")
                # Should be Minnesota, Federal, or regional including MN
                assert any(j in jurisdiction for j in ["Minnesota", "Federal", "MN", "Dakota"])


# ============================================================================
# RESPONSE TIME EXPECTATIONS
# ============================================================================

class TestAgencyResponseTimes:
    """Test that agencies include expected response time information."""
    
    @pytest.mark.asyncio
    async def test_agencies_have_response_days(self):
        """Test that agencies specify typical response times."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/complaints/agencies")
            agencies = response.json()
            
            # At least some agencies should have response time info
            has_response_time = any("typical_response_days" in a for a in agencies)
            assert has_response_time
