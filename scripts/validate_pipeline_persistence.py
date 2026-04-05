import asyncio
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
	sys.path.insert(0, str(ROOT))

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import get_db_session, init_db
from app.models.models import DocumentPipelineIndex
import app.services.document_pipeline as dpmod


async def main() -> int:
	settings = get_settings()
	db_url = settings.database_url
	is_postgres = "postgresql+asyncpg" in db_url or db_url.startswith("postgresql://") or db_url.startswith("postgres://")

	print(f"DB URL: {db_url}")
	print(f"PostgreSQL configured: {is_postgres}")

	await init_db()

	run_id = str(int(time.time() * 1000))
	user_id = f"pg_validation_user_{run_id}"
	filename = f"pg_validation_{run_id}.txt"
	content = f"Postgres persistence validation payload {run_id}".encode("utf-8")
	mime_type = "text/plain"

	pipeline = dpmod.get_document_pipeline()
	doc = await pipeline.ingest(user_id=user_id, filename=filename, content=content, mime_type=mime_type)
	doc_id = doc.id

	async with get_db_session() as db:
		row = (
			await db.execute(
				select(DocumentPipelineIndex).where(DocumentPipelineIndex.doc_id == doc_id)
			)
		).scalar_one_or_none()

	db_row_exists = row is not None
	print(f"DB row exists after ingest: {db_row_exists}")

	index_file = Path("data/documents/index.json")
	backup_file = Path("data/documents/index.json.validation_backup")
	moved_local_index = False

	try:
		if index_file.exists():
			if backup_file.exists():
				backup_file.unlink()
			index_file.rename(backup_file)
			moved_local_index = True
			print("Local fallback index temporarily removed for reload check")

		dpmod._pipeline = None
		fresh_pipeline = dpmod.get_document_pipeline()
		await fresh_pipeline._ensure_db_index_loaded()
		loaded_doc = fresh_pipeline.get_document(doc_id)
		loaded_from_db = loaded_doc is not None

		print(f"Doc reload after restart simulation: {loaded_from_db}")

	finally:
		if moved_local_index and backup_file.exists() and not index_file.exists():
			backup_file.rename(index_file)
			print("Local fallback index restored")

	passed = db_row_exists and loaded_from_db
	print(f"Validation result: {'PASS' if passed else 'FAIL'}")

	if not is_postgres:
		print("NOTE: Environment is not configured to PostgreSQL; validation executed on current DB backend.")

	return 0 if passed else 1


if __name__ == "__main__":
	raise SystemExit(asyncio.run(main()))
