#!/usr/bin/env python3
"""
Semptify SDK Demo - Single File Integration

Demonstrates the complete SDK functionality for onboarding flow.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from sdk import SemptifyClient

def main():
    """Main SDK demo function"""
    print("=== Semptify SDK Demo - Single File Integration ===")
    
    # Initialize the SDK - this is the single entry point
    client = SemptifyClient(base_url="http://localhost:8000")
    
    print(f"SDK Version: 5.0.0")
    print(f"Base URL: {client.base_url}")
    print(f"User-Agent: Semptify-SDK/5.0.0")
    
    # Test all SDK services available in the single client
    print("\n=== SDK Services Available ===")
    
    # Authentication service
    print("1. Authentication Service:")
    try:
        auth_client = client.auth
        print(f"   - Auth Client: {type(auth_client).__name__}")
        
        # Get available storage providers
        providers = auth_client.get_providers()
        print(f"   - Storage Providers: {len(providers)} available")
        for provider in providers:
            print(f"     * {provider.name} ({provider.id})")
        
        # Get OAuth URLs
        google_url = auth_client.get_auth_url("google_drive")
        print(f"   - Google OAuth URL: {google_url[:50]}..." if google_url else "   - Google OAuth: Not available")
        
    except Exception as e:
        print(f"   - Auth Error: {e}")
    
    # Documents service
    print("\n2. Documents Service:")
    try:
        docs_client = client.documents
        print(f"   - Documents Client: {type(docs_client).__name__}")
        print("   - Document upload, intake, and management available")
    except Exception as e:
        print(f"   - Documents Error: {e}")
    
    # Timeline service
    print("\n3. Timeline Service:")
    try:
        timeline_client = client.timeline
        print(f"   - Timeline Client: {type(timeline_client).__name__}")
        print("   - Deadline tracking and event management available")
    except Exception as e:
        print(f"   - Timeline Error: {e}")
    
    # AI Copilot service
    print("\n4. AI Copilot Service:")
    try:
        copilot_client = client.copilot
        print(f"   - Copilot Client: {type(copilot_client).__name__}")
        print("   - AI-powered case analysis and assistance available")
    except Exception as e:
        print(f"   - Copilot Error: {e}")
    
    # Complaints service
    print("\n5. Complaints Service:")
    try:
        complaints_client = client.complaints
        print(f"   - Complaints Client: {type(complaints_client).__name__}")
        print("   - Regulatory agency filing and complaint management available")
    except Exception as e:
        print(f"   - Complaints Error: {e}")
    
    # Briefcase service
    print("\n6. Briefcase Service:")
    try:
        briefcase_client = client.briefcase
        print(f"   - Briefcase Client: {type(briefcase_client).__name__}")
        print("   - Case organization and document management available")
    except Exception as e:
        print(f"   - Briefcase Error: {e}")
    
    # Vault service
    print("\n7. Vault Service:")
    try:
        vault_client = client.vault
        print(f"   - Vault Client: {type(vault_client).__name__}")
        print("   - Secure storage and encryption available")
    except Exception as e:
        print(f"   - Vault Error: {e}")
    
    # Current user info
    print("\n8. Current User:")
    try:
        user = client.current_user
        if user:
            print(f"   - User: {user.display_name} ({user.email})")
            print(f"   - Role: {user.role}")
            print(f"   - Provider: {user.provider}")
        else:
            print("   - No current user (not authenticated)")
    except Exception as e:
        print(f"   - User Error: {e}")
    
    print("\n=== SDK Integration Summary ===")
    print("The Semptify SDK provides a single client interface to all services:")
    print("- Authentication & OAuth flow")
    print("- Document upload and processing")
    print("- Timeline and deadline management")
    print("- AI-powered legal analysis")
    print("- Complaint filing and tracking")
    print("- Case organization (briefcase)")
    print("- Secure vault storage")
    print("\nAll services are accessible through the single SemptifyClient instance.")
    print("This is the single source of truth for all API interactions.")

if __name__ == "__main__":
    main()
