#!/usr/bin/env python3
"""
Test SDK functionality with onboarding flow
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from sdk import SemptifyClient, AuthClient, DocumentClient
from sdk.auth import StorageProvider, UserInfo

def test_sdk_initialization():
    """Test SDK client initialization"""
    print("Testing SDK initialization...")
    
    # Initialize client
    client = SemptifyClient(base_url="http://localhost:8000")
    
    print(f"SDK Version: {client.__class__.__module__}")
    print(f"Base URL: {client.base_url}")
    print(f"Timeout: {client.timeout}")
    
    return client

def test_auth_providers(client):
    """Test authentication providers"""
    print("\nTesting authentication providers...")
    
    try:
        # Access the auth client property to initialize it
        auth_client = client.auth
        providers = auth_client.get_providers()
        print(f"Available providers: {len(providers)}")
        
        for provider in providers:
            print(f"  - {provider.name} ({provider.id}): Connected={provider.connected}")
            
        return providers
    except Exception as e:
        print(f"Error getting providers: {e}")
        return []

def test_auth_urls(client):
    """Test OAuth URLs"""
    print("\nTesting OAuth URLs...")
    
    try:
        auth_client = client.auth
        google_url = auth_client.get_auth_url("google_drive")
        dropbox_url = auth_client.get_auth_url("dropbox")
        onedrive_url = auth_client.get_auth_url("onedrive")
        
        print(f"Google Drive URL: {google_url[:50]}..." if google_url else "Google Drive URL: None")
        print(f"Dropbox URL: {dropbox_url[:50]}..." if dropbox_url else "Dropbox URL: None")
        print(f"OneDrive URL: {onedrive_url[:50]}..." if onedrive_url else "OneDrive URL: None")
        
        return True
    except Exception as e:
        print(f"Error getting auth URLs: {e}")
        return False

def test_current_user(client):
    """Test current user info"""
    print("\nTesting current user...")
    
    try:
        auth_client = client.auth
        user = auth_client.get_current_user()
        if user:
            print(f"Current user: {user.display_name} ({user.email})")
            print(f"Role: {user.role}")
            print(f"Provider: {user.provider}")
        else:
            print("No current user (not authenticated)")
            
        return user
    except Exception as e:
        print(f"Error getting current user: {e}")
        return None

def test_session_validation(client):
    """Test session validation"""
    print("\nTesting session validation...")
    
    try:
        auth_client = client.auth
        is_valid = auth_client.validate_session()
        print(f"Session valid: {is_valid}")
        return is_valid
    except Exception as e:
        print(f"Error validating session: {e}")
        return False

def test_documents_client(client):
    """Test documents client"""
    print("\nTesting documents client...")
    
    try:
        # Test if documents client is accessible
        docs = client.documents
        print(f"Documents client: {type(docs).__name__}")
        
        # Test document upload endpoint (without actually uploading)
        print("Documents client initialized successfully")
        return True
    except Exception as e:
        print(f"Error with documents client: {e}")
        return False

def main():
    """Main test function"""
    print("=== SDK Onboarding Flow Test ===")
    
    # Test SDK initialization
    client = test_sdk_initialization()
    
    # Test authentication components
    providers = test_auth_providers(client)
    test_auth_urls(client)
    user = test_current_user(client)
    test_session_validation(client)
    
    # Test documents client
    test_documents_client(client)
    
    print("\n=== Test Summary ===")
    print(f"SDK initialized: {'Yes' if client else 'No'}")
    print(f"Providers found: {len(providers)}")
    print(f"Current user: {'Yes' if user else 'No'}")
    print("SDK onboarding flow test completed")

if __name__ == "__main__":
    main()
