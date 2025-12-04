"""
Semptify Data Flow Test
=======================
Tests all the actual working data paths and functions
"""
import requests
import json

BASE = "http://localhost:8000"

def test_flow(name, method, path, data=None):
    """Test an endpoint and return result"""
    try:
        url = f"{BASE}{path}"
        if method == "GET":
            r = requests.get(url, timeout=5)
        elif method == "POST":
            r = requests.post(url, json=data, timeout=5)
        
        status = "✅" if r.status_code in [200, 201] else "❌"
        
        # Try to get response details
        try:
            resp = r.json()
            if isinstance(resp, list):
                detail = f"{len(resp)} items"
            elif isinstance(resp, dict):
                detail = f"{len(resp)} keys"
            else:
                detail = str(resp)[:30]
        except:
            detail = f"{len(r.content)} bytes"
        
        print(f"  {status} {method:4} {path:40} [{r.status_code}] {detail}")
        return r.status_code in [200, 201]
    except Exception as e:
        print(f"  ❌ {method:4} {path:40} [ERROR] {str(e)[:30]}")
        return False

def main():
    print()
    print("=" * 70)
    print("  🔄 SEMPTIFY DATA FLOW TEST")
    print("=" * 70)
    print()
    
    results = []
    
    # ===== HEALTH =====
    print("🏥 HEALTH CHECK:")
    results.append(test_flow("Health", "GET", "/health"))
    
    # ===== DOCUMENTS =====
    print()
    print("📄 DOCUMENT FLOWS:")
    results.append(test_flow("List Documents", "GET", "/api/documents/"))
    results.append(test_flow("Document Intake Page", "GET", "/static/document_intake.html"))
    
    # ===== TIMELINE =====
    print()
    print("📅 TIMELINE FLOWS:")
    results.append(test_flow("List Timeline", "GET", "/api/timeline/"))
    results.append(test_flow("Add Event", "POST", "/api/timeline/", {
        "event_type": "notice",
        "title": "Test Flow Event",
        "description": "Testing data flow",
        "event_date": "2025-12-03"
    }))
    
    # ===== CALENDAR =====
    print()
    print("🗓️ CALENDAR FLOWS:")
    results.append(test_flow("List Calendar", "GET", "/api/calendar/"))
    results.append(test_flow("Add Calendar Event", "POST", "/api/calendar/", {
        "title": "Test Hearing",
        "event_type": "hearing",
        "start_datetime": "2025-12-15T10:00:00",
        "description": "Test court hearing"
    }))
    
    # ===== CONTEXT/AI =====
    print()
    print("🤖 CONTEXT & AI FLOWS:")
    results.append(test_flow("Core State", "GET", "/api/core/state"))
    results.append(test_flow("Core Context", "GET", "/api/core/context"))
    results.append(test_flow("UI Widgets", "GET", "/api/ui/widgets"))
    results.append(test_flow("Copilot Status", "GET", "/api/copilot/status"))
    
    # ===== EVICTION DEFENSE =====
    print()
    print("⚖️ EVICTION DEFENSE FLOWS:")
    results.append(test_flow("Eviction Portal", "GET", "/eviction/"))
    results.append(test_flow("Answer Flow", "GET", "/eviction/answer"))
    results.append(test_flow("Counterclaim Flow", "GET", "/eviction/counterclaim"))
    results.append(test_flow("Motions Menu", "GET", "/eviction/motions"))
    results.append(test_flow("Zoom Helper", "GET", "/eviction/zoom"))
    results.append(test_flow("Forms Library", "GET", "/eviction/forms/library"))
    
    # ===== DAKOTA COUNTY =====
    print()
    print("🏛️ DAKOTA COUNTY DATA:")
    results.append(test_flow("Defenses List", "GET", "/dakota/procedures/defenses"))
    results.append(test_flow("Rules", "GET", "/dakota/procedures/rules"))
    
    # ===== STORAGE/AUTH =====
    print()
    print("🔐 AUTH & STORAGE:")
    results.append(test_flow("Session Check", "GET", "/storage/session"))
    results.append(test_flow("Auth Me", "GET", "/api/auth/me"))
    results.append(test_flow("Form Data Hub", "GET", "/api/form-data/"))
    results.append(test_flow("Form Data Summary", "GET", "/api/form-data/summary"))
    
    # ===== SUMMARY =====
    passed = sum(results)
    total = len(results)
    
    print()
    print("=" * 70)
    print(f"  📊 RESULTS: {passed}/{total} flows working ({100*passed//total}%)")
    print("=" * 70)
    
    if passed < total:
        print()
        print("  ⚠️  Some flows need attention!")
    else:
        print()
        print("  🎉 All data flows working!")

if __name__ == "__main__":
    main()
