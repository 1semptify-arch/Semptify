"""
Semptify Trusted Organizations and Invite Codes Configuration
Source of truth for trusted domains and invite codes, loaded from environment/config.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Set, Any

from app.core.user_context import UserRole

logger = logging.getLogger(__name__)


# =============================================================================
# Trusted Domains Configuration
# =============================================================================

def _load_trusted_domains() -> Dict[str, Set[str]]:
    """
    Load trusted domains from environment variables or config file.
    
    Environment variables:
    - TRUSTED_ADVOCATE_DOMAINS: JSON array of domains
    - TRUSTED_LEGAL_DOMAINS: JSON array of domains
    
    Or from config file: trusted_domains.json
    """
    # Try environment variables first
    advocate_env = os.getenv("TRUSTED_ADVOCATE_DOMAINS")
    legal_env = os.getenv("TRUSTED_LEGAL_DOMAINS")
    
    if advocate_env and legal_env:
        try:
            advocate_domains = set(json.loads(advocate_env))
            legal_domains = set(json.loads(legal_env))
            logger.info(f"Loaded {len(advocate_domains)} advocate domains and {len(legal_domains)} legal domains from environment")
            return {
                "advocate": advocate_domains,
                "legal": legal_domains
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse trusted domains from environment: {e}")
    
    # Fallback to config file
    config_file = Path(__file__).resolve().parent.parent.parent / "trusted_domains.json"
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                data = json.load(f)
                advocate_domains = set(data.get("advocate_domains", []))
                legal_domains = set(data.get("legal_domains", []))
                logger.info(f"Loaded {len(advocate_domains)} advocate domains and {len(legal_domains)} legal domains from {config_file}")
                return {
                    "advocate": advocate_domains,
                    "legal": legal_domains
                }
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load trusted domains from {config_file}: {e}")
    
    # Final fallback to minimal defaults (for development only)
    logger.warning("Using minimal trusted domains fallback - configure TRUSTED_ADVOCATE_DOMAINS and TRUSTED_LEGAL_DOMAINS environment variables for production")
    return {
        "advocate": {
            "homeline.org",                    # HOME Line - Tenant Hotline
            "legalaidmn.org",                  # Legal Aid MN
        },
        "legal": {
            "legalaidmn.org",                  # Legal Aid MN
            "umn.edu",                         # U of M Law Clinic
        }
    }


# Global trusted domains
_TRUSTED_DOMAINS = _load_trusted_domains()

TRUSTED_ADVOCATE_DOMAINS = _TRUSTED_DOMAINS["advocate"]
TRUSTED_LEGAL_DOMAINS = _TRUSTED_DOMAINS["legal"]


# =============================================================================
# Invite Codes Configuration
# =============================================================================

def _load_invite_codes() -> Dict[str, Dict[str, Any]]:
    """
    Load invite codes from environment variables or config file.
    
    Environment variable:
    - INVITE_CODES: JSON object of code -> config mappings
    
    Or from config file: invite_codes.json
    
    Format:
    {
        "CODE": {
            "role": "advocate|legal",
            "org": "Organization Name",
            "expires": "2025-12-31",
            "uses_remaining": 50
        }
    }
    """
    # Try environment variable first
    codes_env = os.getenv("INVITE_CODES")
    if codes_env:
        try:
            raw_codes = json.loads(codes_env)
            processed_codes = {}
            for code, config in raw_codes.items():
                processed_codes[code.upper()] = {
                    "role": UserRole(config["role"]),
                    "org": config["org"],
                    "expires": datetime.fromisoformat(config["expires"]),
                    "uses_remaining": config["uses_remaining"]
                }
            logger.info(f"Loaded {len(processed_codes)} invite codes from environment")
            return processed_codes
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse invite codes from environment: {e}")
    
    # Fallback to config file
    config_file = Path(__file__).resolve().parent.parent.parent / "invite_codes.json"
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                raw_codes = json.load(f)
                processed_codes = {}
                for code, config in raw_codes.items():
                    processed_codes[code.upper()] = {
                        "role": UserRole(config["role"]),
                        "org": config["org"],
                        "expires": datetime.fromisoformat(config["expires"]),
                        "uses_remaining": config["uses_remaining"]
                    }
                logger.info(f"Loaded {len(processed_codes)} invite codes from {config_file}")
                return processed_codes
        except (json.JSONDecodeError, IOError, KeyError, ValueError) as e:
            logger.error(f"Failed to load invite codes from {config_file}: {e}")
    
    # No demo codes in production - return empty dict
    logger.info("No invite codes configured - using empty set for security")
    return {}


# Global invite codes
ACTIVE_INVITE_CODES = _load_invite_codes()


# =============================================================================
# Configuration Management
# =============================================================================

def reload_config():
    """Reload configuration from environment/config files."""
    global _TRUSTED_DOMAINS, TRUSTED_ADVOCATE_DOMAINS, TRUSTED_LEGAL_DOMAINS, ACTIVE_INVITE_CODES
    
    _TRUSTED_DOMAINS = _load_trusted_domains()
    TRUSTED_ADVOCATE_DOMAINS = _TRUSTED_DOMAINS["advocate"]
    TRUSTED_LEGAL_DOMAINS = _TRUSTED_DOMAINS["legal"]
    ACTIVE_INVITE_CODES = _load_invite_codes()
    
    logger.info("Trusted configuration reloaded")