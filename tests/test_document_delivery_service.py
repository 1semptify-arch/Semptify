"""Tests for the document delivery service."""

from unittest.mock import AsyncMock, patch

import pytest

from app.models.document_delivery_models import DeliveryType, SendDocumentRequest
from app.services.document_delivery_service import DocumentDeliveryService


def _send_request(delivery_type: DeliveryType) -> SendDocumentRequest:
    return SendDocumentRequest(
        recipient_id="recipient_123",
        document_id="doc_456",
        delivery_type=delivery_type,
        requires_read_receipt=False,
        message="Please review",
    )


@pytest.mark.anyio
async def test_send_document_review_required_succeeds():
    """A review_required delivery creates an overlay and returns success."""
    service = DocumentDeliveryService(storage_provider=None, sender_user_id="sender_789")
    mock_manager = AsyncMock()
    mock_manager.create_overlay = AsyncMock(return_value=AsyncMock(success=True, overlay_id="ov_1"))

    with patch("app.services.document_delivery_service.get_unified_overlay_manager", return_value=mock_manager):
        response = await service.send_document(
            request=_send_request(DeliveryType.REVIEW_REQUIRED),
            sender_name="Sender Name",
            sender_organization="Org",
            sender_role="advocate",
            recipient_name="Recipient Name",
            document_filename="lease.pdf",
            document_hash="abc123",
        )

    assert response.success is True
    assert response.delivery_id is not None
    assert response.message == "Document sent successfully"
    mock_manager.create_overlay.assert_awaited_once()


@pytest.mark.anyio
async def test_send_document_signature_required_succeeds():
    """A signature_required delivery creates an overlay and returns success."""
    service = DocumentDeliveryService(storage_provider=None, sender_user_id="sender_789")
    mock_manager = AsyncMock()
    mock_manager.create_overlay = AsyncMock(return_value=AsyncMock(success=True, overlay_id="ov_2"))

    with patch("app.services.document_delivery_service.get_unified_overlay_manager", return_value=mock_manager):
        response = await service.send_document(
            request=_send_request(DeliveryType.SIGNATURE_REQUIRED),
            sender_name="Sender Name",
            sender_organization="Org",
            sender_role="legal",
            recipient_name="Recipient Name",
            document_filename="notice.pdf",
            document_hash="def456",
        )

    assert response.success is True
    assert response.delivery_id is not None
    assert response.message == "Document sent successfully"


@pytest.mark.anyio
async def test_send_document_process_server_succeeds():
    """A process_server delivery is now accepted and queued for service."""
    service = DocumentDeliveryService(storage_provider=None, sender_user_id="sender_789")
    mock_manager = AsyncMock()
    mock_manager.create_overlay = AsyncMock(return_value=AsyncMock(success=True, overlay_id="ov_3"))

    with patch("app.services.document_delivery_service.get_unified_overlay_manager", return_value=mock_manager):
        response = await service.send_document(
            request=_send_request(DeliveryType.PROCESS_SERVER),
            sender_name="Sender Name",
            sender_organization="Org",
            sender_role="admin",
            recipient_name="Recipient Name",
            document_filename="summons.pdf",
            document_hash="ghi789",
        )

    assert response.success is True
    assert response.delivery_id is not None
    assert "process server" in response.message.lower()

    # Verify the overlay metadata marks process-server as requested
    call_args = mock_manager.create_overlay.call_args
    overlay_request = call_args.args[0]
    metadata = overlay_request.metadata
    assert metadata["process_server_requested"] is True
    assert metadata["delivery_type"] == DeliveryType.PROCESS_SERVER.value


@pytest.mark.anyio
async def test_send_document_overlay_failure_returns_error():
    """If the overlay cannot be created, the service returns an error."""
    service = DocumentDeliveryService(storage_provider=None, sender_user_id="sender_789")
    mock_manager = AsyncMock()
    mock_manager.create_overlay = AsyncMock(return_value=AsyncMock(success=False, message="storage offline"))

    with patch("app.services.document_delivery_service.get_unified_overlay_manager", return_value=mock_manager):
        response = await service.send_document(
            request=_send_request(DeliveryType.REVIEW_REQUIRED),
            sender_name="Sender Name",
            sender_organization=None,
            sender_role="advocate",
            recipient_name="Recipient Name",
            document_filename="file.pdf",
            document_hash="xyz",
        )

    assert response.success is False
    assert "storage offline" in response.message


@pytest.mark.anyio
async def test_unauthorized_sender_role_rejected():
    """Non-sender roles cannot send documents."""
    service = DocumentDeliveryService(storage_provider=None, sender_user_id="sender_789")
    response = await service.send_document(
        request=_send_request(DeliveryType.REVIEW_REQUIRED),
        sender_name="Tenant",
        sender_organization=None,
        sender_role="tenant",
        recipient_name="Recipient",
        document_filename="file.pdf",
        document_hash="xyz",
    )

    assert response.success is False
    assert "cannot send documents" in response.message.lower()
