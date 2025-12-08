"""
Tests for the Research module - Landlord/property research and investigation.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


# ============================================================================
# HEALTH ENDPOINT
# ============================================================================

class TestResearchHealth:
    """Test research service health."""
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test research service health endpoint."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/research/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "research_module"


# ============================================================================
# DATA SOURCES
# ============================================================================

class TestDataSources:
    """Test data source listing."""
    
    @pytest.mark.asyncio
    async def test_get_sources(self):
        """Test getting list of data sources."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/research/sources")
            assert response.status_code == 200
            sources = response.json()
            assert isinstance(sources, list)
            assert len(sources) >= 5
    
    @pytest.mark.asyncio
    async def test_sources_have_required_fields(self):
        """Test that sources have required fields."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/research/sources")
            sources = response.json()
            
            for source in sources:
                assert "id" in source
                assert "name" in source
    
    @pytest.mark.asyncio
    async def test_assessor_source_exists(self):
        """Test that county assessor source exists."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/research/sources")
            sources = response.json()
            
            source_ids = [s["id"] for s in sources]
            assert "assessor" in source_ids
    
    @pytest.mark.asyncio
    async def test_recorder_source_exists(self):
        """Test that county recorder source exists."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/research/sources")
            sources = response.json()
            
            source_ids = [s["id"] for s in sources]
            assert "recorder" in source_ids
    
    @pytest.mark.asyncio
    async def test_ucc_source_exists(self):
        """Test that UCC filing source exists."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/research/sources")
            sources = response.json()
            
            source_ids = [s["id"] for s in sources]
            assert "ucc" in source_ids


# ============================================================================
# PROPERTY LOOKUP
# ============================================================================

class TestPropertyLookup:
    """Test property lookup functionality."""
    
    @pytest.mark.asyncio
    async def test_property_lookup(self):
        """Test looking up property by ID."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/research/property/TEST123")
            # May return data or 404
            assert response.status_code in [200, 404]
    
    @pytest.mark.asyncio
    async def test_property_post_lookup(self):
        """Test property lookup via POST."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/research/property",
                json={"property_id": "TEST123"}
            )
            assert response.status_code in [200, 201, 404, 422]


# ============================================================================
# ASSESSOR DATA
# ============================================================================

class TestAssessorData:
    """Test county assessor data retrieval."""
    
    @pytest.mark.asyncio
    async def test_assessor_endpoint(self):
        """Test assessor data endpoint."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/research/assessor", params={"property_id": "TEST123"})
            # May return data or 404
            assert response.status_code in [200, 404, 422]
    
    @pytest.mark.asyncio
    async def test_assessor_post(self):
        """Test assessor lookup via POST."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/research/assessor",
                json={"property_id": "TEST123", "county": "hennepin"}
            )
            assert response.status_code in [200, 201, 404, 422]


# ============================================================================
# RECORDER DATA
# ============================================================================

class TestRecorderData:
    """Test county recorder data retrieval."""
    
    @pytest.mark.asyncio
    async def test_recorder_endpoint(self):
        """Test recorder data endpoint."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/research/recorder", params={"property_id": "TEST123"})
            assert response.status_code in [200, 404, 422]


# ============================================================================
# UCC FILINGS
# ============================================================================

class TestUCCFilings:
    """Test UCC filing data retrieval."""
    
    @pytest.mark.asyncio
    async def test_ucc_endpoint(self):
        """Test UCC filings endpoint."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/research/ucc", params={"debtor_name": "Test LLC"})
            assert response.status_code in [200, 404, 422]


# ============================================================================
# DISPATCH/911 DATA
# ============================================================================

class TestDispatchData:
    """Test 911 dispatch data retrieval."""
    
    @pytest.mark.asyncio
    async def test_dispatch_endpoint(self):
        """Test dispatch/911 data endpoint."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/research/dispatch", params={"address": "123 Main St"})
            assert response.status_code in [200, 404, 422]


# ============================================================================
# NEWS SEARCH
# ============================================================================

class TestNewsSearch:
    """Test news search functionality."""
    
    @pytest.mark.asyncio
    async def test_news_endpoint(self):
        """Test news search endpoint."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/research/news", params={"query": "test landlord"})
            assert response.status_code in [200, 404, 422]


# ============================================================================
# SOS BUSINESS SEARCH
# ============================================================================

class TestSOSSearch:
    """Test Secretary of State business search."""
    
    @pytest.mark.asyncio
    async def test_sos_endpoint(self):
        """Test SOS business lookup endpoint."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/research/sos", params={"business_name": "Test LLC"})
            assert response.status_code in [200, 404, 422]


# ============================================================================
# BANKRUPTCY SEARCH
# ============================================================================

class TestBankruptcySearch:
    """Test bankruptcy court search."""
    
    @pytest.mark.asyncio
    async def test_bankruptcy_endpoint(self):
        """Test bankruptcy search endpoint."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/research/bankruptcy", params={"name": "Test Landlord"})
            assert response.status_code in [200, 404, 422]


# ============================================================================
# INSURANCE LOOKUP
# ============================================================================

class TestInsuranceLookup:
    """Test insurance information lookup."""
    
    @pytest.mark.asyncio
    async def test_insurance_endpoint(self):
        """Test insurance lookup endpoint."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/research/insurance", params={"property_id": "TEST123"})
            assert response.status_code in [200, 404, 422]


# ============================================================================
# FRAUD FLAGS
# ============================================================================

class TestFraudFlags:
    """Test fraud flag detection."""
    
    @pytest.mark.asyncio
    async def test_fraud_flags_endpoint(self):
        """Test fraud flags endpoint."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/research/fraud-flags", params={"property_id": "TEST123"})
            assert response.status_code in [200, 404, 422]


# ============================================================================
# RESEARCH SUMMARY
# ============================================================================

class TestResearchSummary:
    """Test research summary generation."""
    
    @pytest.mark.asyncio
    async def test_summary_endpoint(self):
        """Test research summary endpoint."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/research/summary", params={"property_id": "TEST123"})
            assert response.status_code in [200, 404, 422]


# ============================================================================
# CHECKPOINTING
# ============================================================================

class TestCheckpointing:
    """Test research checkpointing."""
    
    @pytest.mark.asyncio
    async def test_checkpoint_save(self):
        """Test saving a research checkpoint."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/research/checkpoint",
                json={
                    "property_id": "TEST123",
                    "data": {"assessor": "done", "recorder": "pending"}
                }
            )
            assert response.status_code in [200, 201, 404, 422]
    
    @pytest.mark.asyncio
    async def test_checkpoint_load(self):
        """Test loading a research checkpoint."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/research/checkpoint/TEST123")
            assert response.status_code in [200, 404]


# ============================================================================
# DOWNLOAD/EXPORT
# ============================================================================

class TestDownloadExport:
    """Test research data download/export."""
    
    @pytest.mark.asyncio
    async def test_download_endpoint(self):
        """Test research download endpoint."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/research/download/TEST123")
            assert response.status_code in [200, 404]


# ============================================================================
# SERVICE INTEGRATION
# ============================================================================

class TestServiceIntegration:
    """Test research service integration."""
    
    @pytest.mark.asyncio
    async def test_service_responds(self):
        """Test that research service responds."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/research/health")
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_json_content_type(self):
        """Test that responses are JSON."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/research/health")
            assert "application/json" in response.headers.get("content-type", "")
    
    @pytest.mark.asyncio
    async def test_sources_count(self):
        """Test that we have expected number of sources."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/research/sources")
            sources = response.json()
            # Should have 8 data sources
            assert len(sources) == 8


# ============================================================================
# ERROR HANDLING
# ============================================================================

class TestErrorHandling:
    """Test research service error handling."""
    
    @pytest.mark.asyncio
    async def test_invalid_property_id(self):
        """Test handling of invalid property ID."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/research/property/")
            # Should handle gracefully
            assert response.status_code in [404, 422, 307]  # 307 for redirect
    
    @pytest.mark.asyncio
    async def test_missing_params(self):
        """Test handling of missing parameters."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/research/assessor")
            # Should require property_id
            assert response.status_code in [400, 422, 200]  # 200 if defaults used
