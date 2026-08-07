#!/usr/bin/env python
"""
Debug OAuth configuration and test basic connectivity
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import Settings
from app.modules.onboarding.config import OnboardingConfig


def test_oauth_config():
    """Test basic OAuth configuration"""
    print("🔍 Testing OAuth Configuration")
    print("=" * 50)

    # Check environment variables
    settings = Settings.get_settings()
    print(f"GOOGLE_DRIVE_CLIENT_ID: {'✅ Set' if settings.GOOGLE_DRIVE_CLIENT_ID else '❌ Missing'}")
    print(f"GOOGLE_DRIVE_CLIENT_SECRET: {'✅ Set' if settings.GOOGLE_DRIVE_CLIENT_SECRET else '❌ Missing'}")

    # Test onboarding config
    config = OnboardingConfig()
    print(f"Allowed providers: {config.allowed_providers}")
    print(f"Route prefix: {config.route_prefix}")

    # Test OAuth URL building
    try:
        callback_url = "https://semptify.org/onboarding/callback/google_drive"
        state = "test-state-123"

        # This is the basic OAuth URL format
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?client_id={settings.GOOGLE_DRIVE_CLIENT_ID}&redirect_uri={callback_url}&response_type=code&scope=https://www.googleapis.com/auth/drive&state={state}&access_type=offline"

        print("\n✅ OAuth URL can be built:")
        print(f"Length: {len(auth_url)} chars")
        print(f"Contains client_id: {'✅' if settings.GOOGLE_DRIVE_CLIENT_ID in auth_url else '❌'}")

    except Exception as e:
        print(f"❌ OAuth URL building failed: {e}")
        return False

    return True


if __name__ == "__main__":
    test_oauth_config()
