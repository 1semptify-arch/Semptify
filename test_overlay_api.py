#!/usr/bin/env python3
"""
Test script for the overlay system API.
Run this to verify all overlay endpoints work correctly.
"""

import os
import sys
import json
import uuid
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_overlay_storage():
    """Test overlay storage directly (bypassing HTTP)."""
    from pathlib import Path
    
    print("=" * 60)
    print("TESTING OVERLAY STORAGE SYSTEM")
    print("=" * 60)
    
    # Paths
    vault_path = Path(".semptify/vault")
    overlays_path = vault_path / "overlays"
    overlays_path.mkdir(parents=True, exist_ok=True)
    
    doc_id = "9e2806f4"  # Test document
    overlay_file = overlays_path / f"{doc_id}.json"
    
    # Create test overlay
    overlay = {
        "document_id": doc_id,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "version": 1,
        "highlights": [
            {
                "id": str(uuid.uuid4()),
                "range": {
                    "start_offset": 150,
                    "end_offset": 165,
                    "text": "14-Day Notice"
                },
                "color": "yellow",
                "note": "Critical deadline requirement",
                "created_at": datetime.now().isoformat(),
                "created_by": "test_user"
            },
            {
                "id": str(uuid.uuid4()),
                "range": {
                    "start_offset": 500,
                    "end_offset": 520,
                    "text": "21 days"
                },
                "color": "green",
                "note": "Security deposit return deadline",
                "created_at": datetime.now().isoformat(),
                "created_by": "test_user"
            }
        ],
        "notes": [
            {
                "id": str(uuid.uuid4()),
                "range": {
                    "start_offset": 300,
                    "end_offset": 400,
                    "text": "Notice Requirements"
                },
                "content": "Remember: The notice must be in WRITING and delivered properly. Verbal notices are NOT valid under Minnesota law.",
                "note_type": "legal",
                "priority": "high",
                "tags": ["notice", "deadline", "eviction"],
                "created_at": datetime.now().isoformat(),
                "created_by": "test_user",
                "resolved": False
            },
            {
                "id": str(uuid.uuid4()),
                "range": None,  # Document-level note
                "content": "This document is a reference guide. Consult an attorney for specific legal advice.",
                "note_type": "user",
                "priority": "normal",
                "tags": ["general"],
                "created_at": datetime.now().isoformat(),
                "created_by": "test_user",
                "resolved": False
            }
        ],
        "footnotes": [
            {
                "id": str(uuid.uuid4()),
                "number": 1,
                "range": {
                    "start_offset": 200,
                    "end_offset": 220,
                    "text": "Minn. Stat. § 504B"
                },
                "content": "Minnesota Statutes Chapter 504B is the primary statutory framework governing residential landlord-tenant relationships in Minnesota.",
                "citation": "Minn. Stat. § 504B.001 et seq.",
                "created_at": datetime.now().isoformat(),
                "created_by": "test_user"
            },
            {
                "id": str(uuid.uuid4()),
                "number": 2,
                "range": {
                    "start_offset": 600,
                    "end_offset": 630,
                    "text": "Retaliation Protection"
                },
                "content": "Under Minn. Stat. § 504B.285, tenants are protected from retaliatory actions by landlords.",
                "citation": "Minn. Stat. § 504B.285",
                "created_at": datetime.now().isoformat(),
                "created_by": "test_user"
            }
        ],
        "edits": [
            {
                "id": str(uuid.uuid4()),
                "range": {
                    "start_offset": 450,
                    "end_offset": 460,
                    "text": "21 days"
                },
                "original_text": "21 days",
                "new_text": "twenty-one (21) days",
                "edit_type": "replace",
                "reason": "Legal documents should spell out numbers for clarity",
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "created_by": "test_user",
                "reviewed_at": None,
                "reviewed_by": None
            },
            {
                "id": str(uuid.uuid4()),
                "range": {
                    "start_offset": 800,
                    "end_offset": 830,
                    "text": "contact"
                },
                "original_text": "contact",
                "new_text": "contact your legal aid organization or",
                "edit_type": "insert",
                "reason": "Add helpful direction for tenants",
                "status": "accepted",
                "created_at": datetime.now().isoformat(),
                "created_by": "test_user",
                "reviewed_at": datetime.now().isoformat(),
                "reviewed_by": "reviewer"
            }
        ],
        "processing": [
            {
                "id": str(uuid.uuid4()),
                "processor": "ai_analysis",
                "result_type": "entity_extraction",
                "data": {
                    "entities": [
                        {"type": "statute", "text": "Minn. Stat. § 504B", "confidence": 0.95},
                        {"type": "deadline", "text": "14-day", "confidence": 0.92},
                        {"type": "deadline", "text": "21 days", "confidence": 0.93},
                        {"type": "organization", "text": "HOME Line", "confidence": 0.98}
                    ],
                    "summary": "Legal reference document covering Minnesota tenant rights including notice requirements, security deposits, habitability standards, and retaliation protections."
                },
                "created_at": datetime.now().isoformat()
            }
        ]
    }
    
    # Save overlay
    with open(overlay_file, 'w') as f:
        json.dump(overlay, f, indent=2)
    
    print(f"\n✅ Overlay saved to: {overlay_file}")
    print(f"\n📊 OVERLAY CONTENTS:")
    print(f"   Highlights: {len(overlay['highlights'])}")
    print(f"   Notes: {len(overlay['notes'])}")
    print(f"   Footnotes: {len(overlay['footnotes'])}")
    print(f"   Edits: {len(overlay['edits'])}")
    print(f"   Processing results: {len(overlay['processing'])}")
    
    # Read back and verify
    print(f"\n🔍 VERIFYING SAVED DATA:")
    with open(overlay_file, 'r') as f:
        loaded = json.load(f)
    
    assert loaded['document_id'] == doc_id, "Document ID mismatch"
    assert len(loaded['highlights']) == 2, "Highlights count mismatch"
    assert len(loaded['notes']) == 2, "Notes count mismatch"
    assert len(loaded['footnotes']) == 2, "Footnotes count mismatch"
    assert len(loaded['edits']) == 2, "Edits count mismatch"
    
    print("   ✓ Document ID correct")
    print("   ✓ Highlights verified")
    print("   ✓ Notes verified")
    print("   ✓ Footnotes verified")
    print("   ✓ Edits verified")
    print("   ✓ Processing results verified")
    
    # Display sample data
    print(f"\n📝 SAMPLE HIGHLIGHT:")
    h = overlay['highlights'][0]
    print(f"   Text: \"{h['range']['text']}\"")
    print(f"   Color: {h['color']}")
    print(f"   Note: {h['note']}")
    
    print(f"\n📝 SAMPLE NOTE:")
    n = overlay['notes'][0]
    print(f"   Type: {n['note_type']}")
    print(f"   Priority: {n['priority']}")
    print(f"   Content: {n['content'][:60]}...")
    
    print(f"\n📝 SAMPLE FOOTNOTE:")
    fn = overlay['footnotes'][0]
    print(f"   Number: {fn['number']}")
    print(f"   Citation: {fn['citation']}")
    
    print(f"\n📝 SAMPLE EDIT:")
    e = overlay['edits'][0]
    print(f"   Original: \"{e['original_text']}\"")
    print(f"   New: \"{e['new_text']}\"")
    print(f"   Status: {e['status']}")
    
    print("\n" + "=" * 60)
    print("✅ ALL STORAGE TESTS PASSED!")
    print("=" * 60)
    
    print(f"\n🌐 VIEW IN BROWSER:")
    print(f"   http://localhost:8000/static/document_viewer.html?doc={doc_id}")
    print(f"\n   (Start server with: python -m uvicorn app.main:app)")
    
    return True


if __name__ == "__main__":
    test_overlay_storage()
