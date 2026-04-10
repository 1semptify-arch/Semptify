from pathlib import Path

import pytest

from app.services.vault_upload_service import VaultDocumentIndex, VaultUploadService


def _isolated_vault_service(tmp_path) -> VaultUploadService:
    service = VaultUploadService()
    service.index = VaultDocumentIndex(data_dir=str(tmp_path / "vault_index"))
    service._local_dir = tmp_path / "vault_storage"
    service._local_dir.mkdir(parents=True, exist_ok=True)
    return service


@pytest.mark.anyio
async def test_upload_creates_overlay_manifest(tmp_path, monkeypatch):
    service = _isolated_vault_service(tmp_path)
    overlays = []

    def fake_overlay(doc, overlay_type, payload, metadata=None):
        overlays.append(
            {
                "vault_id": doc.vault_id,
                "overlay_type": overlay_type,
                "payload": payload,
                "metadata": metadata,
            }
        )

    monkeypatch.setattr(service, "_create_overlay_record", fake_overlay)

    doc = await service.upload(
        user_id="GUtest1234",
        filename="lease.pdf",
        content=b"pdf-bytes",
        mime_type="application/pdf",
        source_module="documents",
        storage_provider="local",
    )

    assert doc is not None
    assert overlays
    assert overlays[0]["overlay_type"] == "vault_upload_manifest"
    assert overlays[0]["payload"]["sha256_hash"] == doc.sha256_hash


@pytest.mark.anyio
async def test_mark_processed_and_update_type_emit_overlay_records(tmp_path, monkeypatch):
    service = _isolated_vault_service(tmp_path)
    overlays = []

    def fake_overlay(doc, overlay_type, payload, metadata=None):
        overlays.append(
            {
                "vault_id": doc.vault_id,
                "overlay_type": overlay_type,
                "payload": payload,
                "metadata": metadata,
            }
        )

    monkeypatch.setattr(service, "_create_overlay_record", fake_overlay)

    doc = await service.upload(
        user_id="GUtest1234",
        filename="notice.txt",
        content=b"notice data",
        mime_type="text/plain",
        source_module="intake",
        storage_provider="local",
    )

    service.mark_processed(doc.vault_id, extracted_data={"entities": ["tenant"]})
    service.update_document_type(doc.vault_id, "notice")

    overlay_types = [item["overlay_type"] for item in overlays]
    assert "document_extraction" in overlay_types
    assert "document_classification" in overlay_types


def test_vault_index_rejects_immutable_field_mutation(tmp_path):
    index = VaultDocumentIndex(data_dir=str(tmp_path / "vault_index"))

    from app.services.vault_upload_service import VaultDocument

    doc = VaultDocument(
        vault_id="v1",
        user_id="GUtest1234",
        filename="lease.pdf",
        safe_filename="v1.pdf",
        sha256_hash="abc",
        file_size=10,
        mime_type="application/pdf",
        document_type="lease",
        description=None,
        tags=[],
        storage_path=str(Path("x") / "v1.pdf"),
        storage_provider="local",
        certificate_id="c1",
        uploaded_at="2026-04-05T00:00:00+00:00",
    )
    index.add(doc)

    with pytest.raises(ValueError):
        index.update("v1", sha256_hash="different")


@pytest.mark.anyio
async def test_upload_rejects_disallowed_extension(tmp_path):
    service = _isolated_vault_service(tmp_path)

    with pytest.raises(ValueError):
        await service.upload(
            user_id="GUtest1234",
            filename="malware.exe",
            content=b"bad",
            mime_type="application/octet-stream",
            source_module="documents",
            storage_provider="local",
        )
