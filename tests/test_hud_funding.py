"""
Tests for the HUD Funding Guide module - Federal housing program information.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


# ============================================================================
# PROGRAMS ENDPOINT
# ============================================================================

class TestHUDPrograms:
    """Test HUD funding program listing."""
    
    @pytest.mark.asyncio
    async def test_get_all_programs(self):
        """Test listing all HUD funding programs."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/hud-funding/programs")
            assert response.status_code == 200
            programs = response.json()
            assert isinstance(programs, list)
            assert len(programs) >= 10  # Should have multiple programs
    
    @pytest.mark.asyncio
    async def test_programs_have_required_fields(self):
        """Test that programs have required fields."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/hud-funding/programs")
            programs = response.json()
            
            required_fields = ["id", "name", "program_type", "description"]
            for program in programs:
                for field in required_fields:
                    assert field in program, f"Program missing {field}"
    
    @pytest.mark.asyncio
    async def test_lihtc_program_exists(self):
        """Test that LIHTC (Low-Income Housing Tax Credit) exists."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/hud-funding/programs")
            programs = response.json()
            
            program_ids = [p["id"] for p in programs]
            # Should have either 9% or 4% LIHTC
            has_lihtc = any("lihtc" in pid.lower() for pid in program_ids)
            assert has_lihtc
    
    @pytest.mark.asyncio
    async def test_section_8_exists(self):
        """Test that Section 8 programs exist."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/hud-funding/programs")
            programs = response.json()
            
            program_ids = [p["id"] for p in programs]
            has_section_8 = any("section_8" in pid.lower() for pid in program_ids)
            assert has_section_8


# ============================================================================
# PROGRAM TYPES
# ============================================================================

class TestProgramTypes:
    """Test program type categorization."""
    
    @pytest.mark.asyncio
    async def test_programs_have_types(self):
        """Test that all programs have a program_type."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/hud-funding/programs")
            programs = response.json()
            
            for program in programs:
                assert "program_type" in program
                assert program["program_type"] in [
                    "tax_credit", "voucher", "grant", "tax_deduction", 
                    "loan", "insurance", "other"
                ]
    
    @pytest.mark.asyncio
    async def test_tax_credits_exist(self):
        """Test that tax credit programs exist."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/hud-funding/programs")
            programs = response.json()
            
            tax_credits = [p for p in programs if p.get("program_type") == "tax_credit"]
            assert len(tax_credits) >= 2
    
    @pytest.mark.asyncio
    async def test_voucher_programs_exist(self):
        """Test that voucher programs exist."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/hud-funding/programs")
            programs = response.json()
            
            vouchers = [p for p in programs if p.get("program_type") == "voucher"]
            assert len(vouchers) >= 1


# ============================================================================
# RENT RESTRICTIONS
# ============================================================================

class TestRentRestrictions:
    """Test that programs include rent restriction information."""
    
    @pytest.mark.asyncio
    async def test_programs_have_rent_restrictions(self):
        """Test that programs specify rent restrictions."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/hud-funding/programs")
            programs = response.json()
            
            # Most affordable housing programs should have restrictions
            has_restrictions = any("rent_restrictions" in p for p in programs)
            assert has_restrictions
    
    @pytest.mark.asyncio
    async def test_affordability_years(self):
        """Test that programs specify affordability period."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/hud-funding/programs")
            programs = response.json()
            
            # Programs with rent restrictions should have affordability years
            for program in programs:
                if program.get("rent_restrictions") and program["rent_restrictions"] != "None":
                    assert "affordability_years" in program


# ============================================================================
# LANDLORD BENEFITS
# ============================================================================

class TestLandlordBenefits:
    """Test that programs explain landlord benefits (for fraud detection)."""
    
    @pytest.mark.asyncio
    async def test_programs_explain_benefits(self):
        """Test that programs describe landlord benefits."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/hud-funding/programs")
            programs = response.json()
            
            # Most programs should explain landlord benefits
            has_benefits = any("benefit_to_landlord" in p for p in programs)
            assert has_benefits
    
    @pytest.mark.asyncio
    async def test_opportunity_zone_no_restrictions(self):
        """Test that Opportunity Zone has no rent restrictions."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/hud-funding/programs")
            programs = response.json()
            
            oz = next((p for p in programs if "opportunity_zone" in p["id"]), None)
            if oz:
                # OZ should note NO rent restrictions (key fraud indicator)
                restrictions = oz.get("rent_restrictions", "").upper()
                assert "NONE" in restrictions or "NO" in restrictions


# ============================================================================
# SPECIFIC PROGRAMS
# ============================================================================

class TestSpecificPrograms:
    """Test specific important programs exist."""
    
    @pytest.mark.asyncio
    async def test_section_202_elderly(self):
        """Test Section 202 elderly housing program exists."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/hud-funding/programs")
            programs = response.json()
            
            program_ids = [p["id"] for p in programs]
            assert "section_202" in program_ids
    
    @pytest.mark.asyncio
    async def test_section_811_disability(self):
        """Test Section 811 disability housing program exists."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/hud-funding/programs")
            programs = response.json()
            
            program_ids = [p["id"] for p in programs]
            assert "section_811" in program_ids
    
    @pytest.mark.asyncio
    async def test_home_program(self):
        """Test HOME Investment Partnerships program exists."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/hud-funding/programs")
            programs = response.json()
            
            program_ids = [p["id"] for p in programs]
            assert "home_program" in program_ids
    
    @pytest.mark.asyncio
    async def test_cdbg_program(self):
        """Test CDBG program exists."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/hud-funding/programs")
            programs = response.json()
            
            program_ids = [p["id"] for p in programs]
            assert "cdbg" in program_ids
    
    @pytest.mark.asyncio
    async def test_historic_tax_credit(self):
        """Test Historic Rehabilitation Tax Credit exists."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/hud-funding/programs")
            programs = response.json()
            
            program_ids = [p["id"] for p in programs]
            has_historic = any("historic" in pid.lower() for pid in program_ids)
            assert has_historic


# ============================================================================
# ENERGY/GREEN PROGRAMS
# ============================================================================

class TestEnergyPrograms:
    """Test energy efficiency and green programs."""
    
    @pytest.mark.asyncio
    async def test_solar_itc_exists(self):
        """Test Solar Investment Tax Credit exists."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/hud-funding/programs")
            programs = response.json()
            
            program_ids = [p["id"] for p in programs]
            has_solar = any("solar" in pid.lower() or "itc" in pid.lower() for pid in program_ids)
            assert has_solar
    
    @pytest.mark.asyncio
    async def test_179d_energy_deduction(self):
        """Test Section 179D energy deduction exists."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/hud-funding/programs")
            programs = response.json()
            
            program_ids = [p["id"] for p in programs]
            has_179d = any("179d" in pid.lower() for pid in program_ids)
            assert has_179d


# ============================================================================
# PROGRAM COUNT
# ============================================================================

class TestProgramCoverage:
    """Test comprehensive program coverage."""
    
    @pytest.mark.asyncio
    async def test_minimum_program_count(self):
        """Test that we have comprehensive program coverage."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/hud-funding/programs")
            programs = response.json()
            
            # Should have at least 10 programs for comprehensive coverage
            assert len(programs) >= 10
    
    @pytest.mark.asyncio
    async def test_programs_have_descriptions(self):
        """Test all programs have descriptions."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/hud-funding/programs")
            programs = response.json()
            
            for program in programs:
                assert "description" in program
                assert len(program["description"]) > 20  # Meaningful description
