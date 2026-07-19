#!/usr/bin/env python3
"""
Simple verification script to check that the legal_intel project is set up correctly.
Run this after installing dependencies to verify the installation.
"""

import os
import sys

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")

    try:
        import fastapi

        print("✓ fastapi")
    except ImportError as e:
        print(f"✗ fastapi: {e}")
        return False

    try:
        import uvicorn

        print("✓ uvicorn")
    except ImportError as e:
        print(f"✗ uvicorn: {e}")
        return False

    try:
        import sqlalchemy

        print("✓ sqlalchemy")
    except ImportError as e:
        print(f"✗ sqlalchemy: {e}")
        return False

    try:
        import asyncpg

        print("✓ asyncpg")
    except ImportError as e:
        print(f"✗ asyncpg: {e}")
        return False

    try:
        import pydantic

        print("✓ pydantic")
    except ImportError as e:
        print(f"✗ pydantic: {e}")
        return False

    try:
        import httpx

        print("✓ httpx")
    except ImportError as e:
        print(f"✗ httpx: {e}")
        return False

    try:
        from bs4 import BeautifulSoup

        print("✓ beautifulsoup4")
    except ImportError as e:
        print(f"✗ beautifulsoup4: {e}")
        return False

    try:
        import playwright

        print("✓ playwright")
    except ImportError as e:
        print(f"✗ playwright: {e}")
        return False

    return True


def test_app_imports():
    """Test that app modules can be imported."""
    print("\nTesting app module imports...")

    try:
        from app import config

        print("✓ app.config")
    except ImportError as e:
        print(f"✗ app.config: {e}")
        return False

    try:
        from app import db

        print("✓ app.db")
    except ImportError as e:
        print(f"✗ app.db: {e}")
        return False

    try:
        from app import models

        print("✓ app.models")
    except ImportError as e:
        print(f"✗ app.models: {e}")
        return False

    try:
        from app import schemas

        print("✓ app.schemas")
    except ImportError as e:
        print(f"✗ app.schemas: {e}")
        return False

    try:
        from app.crawlers import mcro

        print("✓ app.crawlers.mcro")
    except ImportError as e:
        print(f"✗ app.crawlers.mcro: {e}")
        return False

    try:
        from app.crawlers import sos

        print("✓ app.crawlers.sos")
    except ImportError as e:
        print(f"✗ app.crawlers.sos: {e}")
        return False

    try:
        from app.crawlers import plainsite

        print("✓ app.crawlers.plainsite")
    except ImportError as e:
        print(f"✗ app.crawlers.plainsite: {e}")
        return False

    try:
        from app.crawlers import courtlistener

        print("✓ app.crawlers.courtlistener")
    except ImportError as e:
        print(f"✗ app.crawlers.courtlistener: {e}")
        return False

    try:
        from app.services import patterns

        print("✓ app.services.patterns")
    except ImportError as e:
        print(f"✗ app.services.patterns: {e}")
        return False

    try:
        from app.services import unified_crawler

        print("✓ app.services.unified_crawler")
    except ImportError as e:
        print(f"✗ app.services.unified_crawler: {e}")
        return False

    try:
        from app.routers import crawl

        print("✓ app.routers.crawl")
    except ImportError as e:
        print(f"✗ app.routers.crawl: {e}")
        return False

    try:
        from app.routers import intel

        print("✓ app.routers.intel")
    except ImportError as e:
        print(f"✗ app.routers.intel: {e}")
        return False

    try:
        from app import main

        print("✓ app.main")
    except ImportError as e:
        print(f"✗ app.main: {e}")
        return False

    return True


def test_models():
    """Test that models are defined correctly."""
    print("\nTesting models...")

    try:
        from app.models import Attorney, Case, Docket, Entity, Relationship, SearchCache

        print("✓ All models imported")

        # Check that models have expected attributes
        attorney_attrs = ["id", "name", "bar_number", "state", "firm", "address", "email", "phone", "last_seen"]
        for attr in attorney_attrs:
            if not hasattr(Attorney, attr):
                print(f"✗ Attorney missing attribute: {attr}")
                return False
        print("✓ Attorney model structure OK")

        entity_attrs = ["id", "name", "type", "sos_id", "registered_agent", "address"]
        for attr in entity_attrs:
            if not hasattr(Entity, attr):
                print(f"✗ Entity missing attribute: {attr}")
                return False
        print("✓ Entity model structure OK")

        case_attrs = [
            "id",
            "court",
            "case_number",
            "case_title",
            "case_type",
            "filing_date",
            "status",
            "attorney_id",
            "entity_id",
            "last_crawled",
        ]
        for attr in case_attrs:
            if not hasattr(Case, attr):
                print(f"✗ Case missing attribute: {attr}")
                return False
        print("✓ Case model structure OK")

        return True
    except ImportError as e:
        print(f"✗ Model import failed: {e}")
        return False


def test_schemas():
    """Test that schemas are defined correctly."""
    print("\nTesting schemas...")

    try:
        from app.schemas import Attorney, Case, Docket, Entity, PatternSummary

        print("✓ All schemas imported")
        return True
    except ImportError as e:
        print(f"✗ Schema import failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Legal Intel Engine - Setup Verification")
    print("=" * 60)

    all_passed = True

    if not test_imports():
        all_passed = False

    if not test_app_imports():
        all_passed = False

    if not test_models():
        all_passed = False

    if not test_schemas():
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed!")
        print("\nNext steps:")
        print("1. Configure DATABASE_URL in .env")
        print("2. Create PostgreSQL database: createdb legal_intel")
        print("3. Run: uvicorn app.main:app --reload")
    else:
        print("✗ Some tests failed. Please check the errors above.")
        print("\nTo install dependencies:")
        print("  pip install -r requirements.txt")
        print("  playwright install chromium")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
