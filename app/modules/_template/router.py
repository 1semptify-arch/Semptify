"""
Module Template — FastAPI Router

Skeleton with health check + CRUD endpoints. Replace with your module's
endpoints. Keep routers thin — delegate to service.py.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.request_utils import get_request_user_id
from app.core.security import get_current_user
from app.core.user_context import UserContext
from app.core.utc import utc_now

from .models import ItemCreate, ItemResponse, ItemUpdate
from .service import service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Template Module"])


@router.get("/health")
async def health_check():
    """Health check — no auth required."""
    return {
        "status": "ok",
        "module": "template",
        "lifecycle": "dev_only",
        "timestamp": utc_now().isoformat(),
    }


@router.get("/items", response_model=list[ItemResponse])
async def list_items(
    request: Request,
    user: UserContext = Depends(get_current_user),
):
    """List items for the current user."""
    get_request_user_id(request)
    # TODO: Replace with real list query
    return []


@router.post("/items", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    body: ItemCreate,
    request: Request,
    user: UserContext = Depends(get_current_user),
):
    """Create a new item."""
    user_id = get_request_user_id(request)
    item = await service.create_item(body.name, body.description, user_id)
    return ItemResponse(**item)


@router.get("/items/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: str,
    user: UserContext = Depends(get_current_user),
):
    """Get a specific item by ID."""
    item = await service.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return ItemResponse(**item)


@router.patch("/items/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: str,
    body: ItemUpdate,
    user: UserContext = Depends(get_current_user),
):
    """Update an item."""
    updates = body.dict(exclude_unset=True)
    item = await service.update_item(item_id, **updates)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return ItemResponse(**item)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: str,
    user: UserContext = Depends(get_current_user),
):
    """Delete an item."""
    deleted = await service.delete_item(item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return None
