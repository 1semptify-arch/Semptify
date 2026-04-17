#!/usr/bin/env python3
"""
Test Single File SDK
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from semptify_sdk import SemptifyClient, UserInfo, StorageProvider

def test_single_sdk():
    """Test the single-file SDK implementation"""
    print("=== Single File SDK Test ===")
    
    # Test SDK initialization
    client = SemptifyClient(base_url="http://localhost:8000")
    print(f"SDK Version: 5.0.0")
    print(f"Base URL: {client.base_url}")
    print(f"User-Agent: Semptify-SDK/5.0.0")
    
    # Test all service clients
    print("\n=== Service Clients ===")
    
    # Auth client
    auth = client.auth
    print(f"Auth Client: {type(auth).__name__}")
    
    # Documents client
    docs = client.documents
    print(f"Documents Client: {type(docs).__name__}")
    
    # Timeline client
    timeline = client.timeline
    print(f"Timeline Client: {type(timeline).__name__}")
    
    # Copilot client
    copilot = client.copilot
    print(f"Copilot Client: {type(copilot).__name__}")
    
    # Complaints client
    complaints = client.complaints
    print(f"Complaints Client: {type(complaints).__name__}")
    
    # Briefcase client
    briefcase = client.briefcase
    print(f"Briefcase Client: {type(briefcase).__name__}")
    
    # Vault client
    vault = client.vault
    print(f"Vault Client: {type(vault).__name__}")
    
    # Test data models
    print("\n=== Data Models ===")
    
    user = UserInfo(user_id="test123", provider="google", email="test@example.com")
    print(f"UserInfo: {user}")
    
    provider = StorageProvider(id="google_drive", name="Google Drive", icon="google")
    print(f"StorageProvider: {provider}")
    
    # Test context manager
    print("\n=== Context Manager ===")
    with SemptifyClient("http://localhost:8000") as ctx_client:
        print(f"Context client: {type(ctx_client).__name__}")
        print(f"Context client URL: {ctx_client.base_url}")
    
    print("\n=== Single File SDK Test Complete ===")
    print("All functionality is contained in a single file: semptify_sdk.py")

if __name__ == "__main__":
    test_single_sdk()
