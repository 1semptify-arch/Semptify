#!/usr/bin/env python3
"""
Storage Credentials Setup Script
================================

Quick script to set up storage provider credentials for Semptify.
This will help you configure Google Drive, Dropbox, or OneDrive credentials.
"""

import os
import sys
from pathlib import Path

def setup_google_drive():
    """Setup Google Drive credentials"""
    print("\n=== Google Drive Setup ===")
    print("1. Go to: https://console.cloud.google.com/")
    print("2. Create project or use existing one")
    print("3. Enable Google Drive API")
    print("4. Create OAuth credentials (Web application)")
    print("5. Add redirect URI: http://localhost:8000/storage/google_drive/callback")
    print("6. Copy Client ID and Client Secret")
    
    client_id = input("\nEnter Google Drive Client ID: ").strip()
    client_secret = input("Enter Google Drive Client Secret: ").strip()
    
    if client_id and client_secret:
        # Set environment variables for current session
        os.environ['GOOGLE_DRIVE_CLIENT_ID'] = client_id
        os.environ['GOOGLE_DRIVE_CLIENT_SECRET'] = client_secret
        
        # Create .env file for persistence
        env_file = Path('.env')
        with open(env_file, 'w') as f:
            f.write(f"GOOGLE_DRIVE_CLIENT_ID={client_id}\n")
            f.write(f"GOOGLE_DRIVE_CLIENT_SECRET={client_secret}\n")
        
        print("✅ Google Drive credentials configured!")
        print(f"📁 Created .env file at: {env_file.absolute()}")
        return True
    else:
        print("❌ Invalid credentials. Please try again.")
        return False

def setup_dropbox():
    """Setup Dropbox credentials"""
    print("\n=== Dropbox Setup ===")
    print("1. Go to: https://www.dropbox.com/developers/apps")
    print("2. Create new app (Full Dropbox)")
    print("3. Set redirect URI: http://localhost:8000/storage/dropbox/callback")
    print("4. Copy App Key and App Secret")
    
    app_key = input("\nEnter Dropbox App Key: ").strip()
    app_secret = input("Enter Dropbox App Secret: ").strip()
    
    if app_key and app_secret:
        os.environ['DROPBOX_APP_KEY'] = app_key
        os.environ['DROPBOX_APP_SECRET'] = app_secret
        
        env_file = Path('.env')
        with open(env_file, 'a') as f:
            f.write(f"DROPBOX_APP_KEY={app_key}\n")
            f.write(f"DROPBOX_APP_SECRET={app_secret}\n")
        
        print("✅ Dropbox credentials configured!")
        return True
    else:
        print("❌ Invalid credentials. Please try again.")
        return False

def setup_onedrive():
    """Setup OneDrive credentials"""
    print("\n=== OneDrive Setup ===")
    print("1. Go to: https://portal.azure.com/")
    print("2. Azure Active Directory > App registrations")
    print("3. Create new app registration")
    print("4. Set redirect URI: http://localhost:8000/storage/onedrive/callback")
    print("5. Copy Application ID and Client Secret")
    
    client_id = input("\nEnter OneDrive Client ID: ").strip()
    client_secret = input("Enter OneDrive Client Secret: ").strip()
    
    if client_id and client_secret:
        os.environ['ONEDRIVE_CLIENT_ID'] = client_id
        os.environ['ONEDRIVE_CLIENT_SECRET'] = client_secret
        
        env_file = Path('.env')
        with open(env_file, 'a') as f:
            f.write(f"ONEDRIVE_CLIENT_ID={client_id}\n")
            f.write(f"ONEDRIVE_CLIENT_SECRET={client_secret}\n")
        
        print("✅ OneDrive credentials configured!")
        return True
    else:
        print("❌ Invalid credentials. Please try again.")
        return False

def test_credentials():
    """Test if credentials are properly set"""
    print("\n=== Testing Credentials ===")
    
    providers = {
        'Google Drive': ['GOOGLE_DRIVE_CLIENT_ID', 'GOOGLE_DRIVE_CLIENT_SECRET'],
        'Dropbox': ['DROPBOX_APP_KEY', 'DROPBOX_APP_SECRET'],
        'OneDrive': ['ONEDRIVE_CLIENT_ID', 'ONEDRIVE_CLIENT_SECRET']
    }
    
    for provider, env_vars in providers.items():
        if all(os.environ.get(var) for var in env_vars):
            print(f"✅ {provider}: Configured")
        else:
            missing = [var for var in env_vars if not os.environ.get(var)]
            print(f"❌ {provider}: Missing {', '.join(missing)}")

def main():
    """Main setup script"""
    print("🚀 Semptify Storage Credentials Setup")
    print("=====================================")
    
    while True:
        print("\nSelect storage provider to configure:")
        print("1. Google Drive (Recommended)")
        print("2. Dropbox")
        print("3. OneDrive")
        print("4. Test existing credentials")
        print("5. Exit")
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == '1':
            setup_google_drive()
        elif choice == '2':
            setup_dropbox()
        elif choice == '3':
            setup_onedrive()
        elif choice == '4':
            test_credentials()
        elif choice == '5':
            print("\n👋 Setup complete!")
            break
        else:
            print("❌ Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
