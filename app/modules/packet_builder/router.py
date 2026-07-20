"""Packet Builder Router

REST endpoints for building, inspecting, and downloading curated document
packets. Supports overlay and clean export modes and zip/pdf output formats.
"""

import io

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.capabilities import require_capability
from app.core.security import UserContext, yellow_access

from . import service

router = APIRouter(
    prefix="/api/packet-builder",
    tags=["Packet Builder"],
    dependencies=[Depends(require_capability("app.modules.packet_builder.router"))],
)


class BuildPacketRequest(BaseModel):
    """Request body for POST /api/packet-builder/build."""

    vault_ids: list[str] = Field(default_factory=list)
    case_id: str | None = None
    folder_id: str | None = None
    mode: str
    include_highlights: bool = True
    include_notes: bool = True
    include_footnotes: bool = True
    name: str | None = None

    @field_validator("mode")
    @classmethod
    def _validate_mode(cls, value: str) -> str:
        if value not in ("overlay", "clean"):
            raise ValueError("mode must be overlay or clean")
        return value

    @model_validator(mode="after")
    def _validate_source(self):
        if not self.vault_ids and not self.case_id and not self.folder_id:
            raise ValueError("At least one of vault_ids, case_id, or folder_id is required")
        return self


@router.post("/build")
async def build_packet(
    body: BuildPacketRequest,
    req: Request,
    user: UserContext = Depends(yellow_access),
):
    """Build a new curated packet and return its id and download URL."""
    try:
        result = await service.build_packet(
            user_id=user.user_id,
            name=body.name,
            vault_ids=body.vault_ids,
            case_id=body.case_id,
            folder_id=body.folder_id,
            mode=body.mode,
            include_highlights=body.include_highlights,
            include_notes=body.include_notes,
            include_footnotes=body.include_footnotes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    result["download_url"] = str(req.url_for("download_packet", packet_id=result["packet_id"]))
    return result


@router.get("/packets/{packet_id}")
async def get_packet(packet_id: str, user: UserContext = Depends(yellow_access)):
    """Return metadata for a previously built packet."""
    metadata = await service.get_packet_metadata(packet_id, user.user_id)
    if not metadata:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Packet not found")
    return metadata


@router.get("/packets/{packet_id}/download", name="download_packet")
async def download_packet(
    packet_id: str,
    output_format: str = Query("zip", alias="format"),
    mode: str | None = Query(None),
    user: UserContext = Depends(yellow_access),
):
    """Download a packet as a ZIP or PDF."""
    try:
        result = await service.download_packet(
            packet_id=packet_id,
            user_id=user.user_id,
            output_format=output_format,
            mode=mode,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Packet not found")

    content, filename, media_type = result
    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
