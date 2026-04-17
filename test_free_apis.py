#!/usr/bin/env python3
"""
Test Free API Pack Integration
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

import semptify_free_apis

def test_free_api_pack():
    """Test the free API pack functionality"""
    print("=== Free API Pack Test ===")
    
    # Test API registry
    api = semptify_free_apis.api
    print(f"API Registry: {type(api).__name__}")
    
    # Test all API classes
    print("\n=== API Classes ===")
    
    # Property lookup
    property_lookup = api.property
    print(f"Property Lookup: {type(property_lookup).__name__}")
    
    # Test property methods
    parcel_result = property_lookup.lookup_parcel("Ramsey", "12345")
    print(f"Parcel lookup: {parcel_result}")
    
    address_result = property_lookup.lookup_address("Hennepin", "123 Main St")
    print(f"Address lookup: {address_result}")
    
    # Landlord lookup
    landlord_lookup = api.landlord
    print(f"Landlord Lookup: {type(landlord_lookup).__name__}")
    
    business_result = landlord_lookup.lookup_business("Test LLC")
    print(f"Business lookup: {business_result}")
    
    # Court scraper
    court_scraper = api.courts
    print(f"Court Scraper: {type(court_scraper).__name__}")
    
    eviction_result = court_scraper.search_evictions("John Doe")
    print(f"Eviction search: {eviction_result}")
    
    # Violations
    violations = api.violations
    print(f"Violations: {type(violations).__name__}")
    
    city_violations = violations.city_inspections("Minneapolis", "123 Main St")
    print(f"City violations: {city_violations}")
    
    # Inspections
    inspections = api.inspections
    print(f"Inspections: {type(inspections).__name__}")
    
    hud_result = inspections.hud_reac("PROP123")
    print(f"HUD inspection: {hud_result}")
    
    # Statutes
    statutes = api.statutes
    print(f"Statutes: {type(statutes).__name__}")
    
    statute_result = statutes.get_statute("504B")
    print(f"Statute lookup: {statute_result}")
    
    # Test router
    print("\n=== FastAPI Router ===")
    router = semptify_free_apis.router
    print(f"Router: {type(router).__name__}")
    print(f"Router prefix: {router.prefix}")
    print(f"Router tags: {router.tags}")
    
    print("\n=== Free API Pack Test Complete ===")
    print("All API classes and methods are ready for implementation")

if __name__ == "__main__":
    test_free_api_pack()
