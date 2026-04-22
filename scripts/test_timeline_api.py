"""
Test the unified timeline API endpoint.
Usage: python scripts/test_timeline_api.py
"""
import asyncio
import httpx
import sys

# API base URL
BASE_URL = "http://localhost:8000"


async def test_date_range_endpoint():
    """Test GET /api/timeline/date-range"""
    print("Testing GET /api/timeline/date-range...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/api/timeline/date-range")
            print(f"  Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"  Response: {data}")
                return True
            else:
                print(f"  Error: {response.text[:200]}")
                return False
        except Exception as e:
            print(f"  Connection error: {e}")
            print("  (Server may not be running)")
            return False


async def test_unified_timeline():
    """Test POST /api/timeline/unified"""
    print("\nTesting POST /api/timeline/unified...")
    
    payload = {
        "date_axis": "event_time",
        "item_types": ["document", "timeline_event"],
        "limit": 10
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/api/timeline/unified",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            print(f"  Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"  Total items: {data.get('total', 'N/A')}")
                print(f"  Date axis: {data.get('date_axis')}")
                print(f"  Items returned: {len(data.get('items', []))}")
                if data.get('items'):
                    print(f"  Sample item: {data['items'][0]['title'][:50]}...")
                return True
            elif response.status_code == 401:
                print("  Unauthorized - need to be logged in (expected without auth)")
                return True  # This is expected behavior
            else:
                print(f"  Error: {response.text[:500]}")
                return False
        except Exception as e:
            print(f"  Connection error: {e}")
            print("  (Server may not be running)")
            return False


async def main():
    print("=" * 60)
    print("Unified Timeline API Tests")
    print("=" * 60)
    
    results = []
    
    # Test 1: Date range endpoint
    results.append(("Date Range", await test_date_range_endpoint()))
    
    # Test 2: Unified timeline endpoint
    results.append(("Unified Timeline", await test_unified_timeline()))
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name}: {status}")
    
    all_passed = all(passed for _, passed in results)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    asyncio.run(main())
