"""
Unit tests for the template module scaffold.

Copy this file to your module's tests/ directory and replace with real tests.
Tests are required to progress from dev_only ▸ experimental.
"""

import pytest

from app.modules._template.models import ItemCreate, ItemUpdate
from app.modules._template.service import TemplateService


@pytest.mark.asyncio
async def test_create_item():
    """Test item creation."""
    svc = TemplateService()
    item = await svc.create_item(name="Test", description="desc", user_id="user1")
    assert item["name"] == "Test"
    assert item["created_by"] == "user1"


@pytest.mark.asyncio
async def test_get_item_not_found():
    """Test get returns None for missing item."""
    svc = TemplateService()
    item = await svc.get_item("nonexistent")
    assert item is None


@pytest.mark.asyncio
async def test_delete_item():
    """Test delete returns False for missing item."""
    svc = TemplateService()
    result = await svc.delete_item("nonexistent")
    assert result is False


def test_item_create_validation():
    """Test Pydantic validation."""
    item = ItemCreate(name="Test")
    assert item.name == "Test"
    assert item.description is None

    with pytest.raises(ValueError):
        ItemCreate(name="")


def test_item_update_partial():
    """Test partial update model."""
    update = ItemUpdate(name="New Name")
    assert update.name == "New Name"
    assert update.description is None
