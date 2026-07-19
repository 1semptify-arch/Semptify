import asyncio
import contextlib
import shutil

from app.core.database import init_db
from app.services.vault_upload_service import get_vault_service


async def run():
    # Clean test dir
    test_dir = "data/test_local_vault"
    with contextlib.suppress(Exception):
        shutil.rmtree(test_dir)

    # Initialize database tables for test (SQLite)
    await init_db()

    svc = get_vault_service()
    svc._local_dir = test_dir

    user_id = "testuser"
    filename = "greeting.txt"
    content = b"hello semptify"
    mime_type = "text/plain"

    print("Uploading first time...")
    doc1 = await svc.upload(
        user_id=user_id, filename=filename, content=content, mime_type=mime_type, storage_provider="local"
    )
    print("First upload:", doc1.vault_id, doc1.storage_path, doc1.provider_file_id)

    print("Downloading content...")
    got = await svc.get_document_content(doc1.vault_id)
    print("Downloaded bytes:", got)

    print("Uploading duplicate content...")
    doc2 = await svc.upload(
        user_id=user_id, filename=filename, content=content, mime_type=mime_type, storage_provider="local"
    )
    print("Duplicate upload returned:", doc2.vault_id, doc2.storage_path, doc2.provider_file_id)

    print("Done")


if __name__ == "__main__":
    asyncio.run(run())
    asyncio.run(run())
