"""Tests for the filedored post-processing service."""

from unittest.mock import AsyncMock

import pytest

from app.core.vault_paths import (
    VAULT_FILEDORED_AI_NOTICE,
    VAULT_FILEDORED_OTHER,
    VAULT_FILEDORED_PDF,
)
from app.services.filedored_service import ai_classify_document, process_uploaded_document


class FakeOverlayManager:
    def __init__(self):
        self.storage = object()
        self.created = []

    async def create_overlay(self, req):
        self.created.append(req)


@pytest.fixture
def fake_overlay_manager():
    return FakeOverlayManager()


@pytest.fixture(autouse=True)
def patch_ensure_folder(monkeypatch):
    """Avoid cloud storage calls during AI folder lazy-creation."""
    monkeypatch.setattr(
        "app.services.filedored_service.ensure_filedored_folder",
        AsyncMock(return_value=True),
    )


class TestAiClassifyDocument:
    def test_classifies_notice_from_filename(self):
        label = ai_classify_document("vault-1", b"", "notice_to_quit.pdf")
        assert label == "notice"

    def test_returns_unknown_for_random_filename(self):
        label = ai_classify_document("vault-2", b"", "document_123.pdf")
        assert label == "unknown"

    def test_classifies_content_when_filename_is_generic(self):
        content = b"This is a lease agreement between landlord and tenant."
        label = ai_classify_document("vault-3", content, "doc.pdf")
        assert label == "lease"


class TestProcessUploadedDocument:
    async def test_extension_based_sorting_for_pdf(self, fake_overlay_manager):
        result = await process_uploaded_document(
            vault_id="vault-1",
            user_id="user-1",
            filename="statement.pdf",
            content=b"",
            sha256_hash="abc",
            enable_ai=False,
            overlay_manager=fake_overlay_manager,
        )
        assert result["status"] == "sorted"
        assert result["overlay_path"] == VAULT_FILEDORED_PDF
        assert result["extension"] == "pdf"
        assert len(fake_overlay_manager.created) == 1
        assert fake_overlay_manager.created[0].vault_path == VAULT_FILEDORED_PDF

    async def test_extension_based_sorting_for_unknown_extension(self, fake_overlay_manager):
        result = await process_uploaded_document(
            vault_id="vault-2",
            user_id="user-1",
            filename="backup.7z",
            content=b"",
            sha256_hash="def",
            enable_ai=False,
            overlay_manager=fake_overlay_manager,
        )
        assert result["status"] == "sorted"
        assert result["overlay_path"] == VAULT_FILEDORED_OTHER

    async def test_ai_classification_creates_overlay_with_confidence(self, fake_overlay_manager):
        result = await process_uploaded_document(
            vault_id="vault-3",
            user_id="user-1",
            filename="notice_to_pay_rent.pdf",
            content=b"Notice to pay rent or quit within 14 days.",
            sha256_hash="ghi",
            enable_ai=True,
            overlay_manager=fake_overlay_manager,
        )
        assert result["status"] == "ai_classified"
        assert result["overlay_path"] == VAULT_FILEDORED_AI_NOTICE
        assert result["ai_label"] == "notice"
        assert "ai_confidence" in result
        assert 0.0 < result["ai_confidence"] <= 0.99

        assert len(fake_overlay_manager.created) == 1
        req = fake_overlay_manager.created[0]
        assert req.vault_path == VAULT_FILEDORED_AI_NOTICE
        assert req.payload["ai_confidence"] == result["ai_confidence"]
        assert req.payload["filedored_category"] == "notice"

    async def test_ai_unknown_falls_back_to_extension_sort(self, fake_overlay_manager):
        result = await process_uploaded_document(
            vault_id="vault-4",
            user_id="user-1",
            filename="backup.bin",
            content=b"unknown binary content",
            sha256_hash="jkl",
            enable_ai=True,
            overlay_manager=fake_overlay_manager,
        )
        # The classifier has no strong signal for "backup.bin", so it falls back to
        # extension-based sorting (which lands in OTHER for an unknown extension).
        assert result["status"] == "sorted"
        assert result["overlay_path"] == VAULT_FILEDORED_OTHER

    def test_requires_overlay_manager(self):
        with pytest.raises(RuntimeError, match="overlay_manager is required"):
            # This test is synchronous because the function raises before any await.
            # We call it directly; the coroutine is not awaited, but the check is
            # inside a def, so Python evaluates it when creating the coroutine.
            # To avoid a coroutine never awaited warning, we wrap in asyncio.run.
            import asyncio

            asyncio.run(
                process_uploaded_document(
                    vault_id="vault-5",
                    user_id="user-1",
                    filename="doc.pdf",
                    content=b"",
                    sha256_hash="mno",
                    enable_ai=False,
                    overlay_manager=None,
                )
            )
