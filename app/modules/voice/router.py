"""
Voice API router.

Endpoints:
- POST /api/voice/transcribe
  Browser fallback for when the Web Speech API is unavailable or unsuitable.
  Accepts an audio file, transcribes it via OpenAI Whisper, and discards the
  raw audio. If keep_audio=true, the audio is stored in the user's vault as
  evidence after transcription.
"""

import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import UserContext, green_access
from app.core.utc import utc_now
from app.services.voice_service import transcribe_audio

try:
    from app.services.vault_upload_service import get_vault_service

    HAS_VAULT_SERVICE = True
except ImportError:
    HAS_VAULT_SERVICE = False

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Voice"])


@router.post("/transcribe")
async def transcribe_voice(
    audio: UploadFile = File(...),
    language: str | None = Form(None),
    keep_audio: bool = Form(False),
    user: UserContext = Depends(green_access),
    db: AsyncSession = Depends(get_db),
):
    """Transcribe an uploaded audio clip. Raw audio is discarded unless keep_audio is true."""
    audio_bytes = await audio.read()
    await audio.close()

    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    result = await transcribe_audio(
        audio_bytes,
        filename=audio.filename or "audio.webm",
        language=language,
    )

    if keep_audio and result.get("success") and HAS_VAULT_SERVICE:
        try:
            real_token = user.access_token if user else None
            if not real_token or real_token in ("auto", "no-token"):
                from app.core.auto_refresh import ensure_valid_token

                _, token_obj, _ = await ensure_valid_token(user.user_id, db)
                real_token = token_obj.access_token if token_obj else None

            vault_service = get_vault_service()
            mime_type = audio.content_type or "audio/webm"
            vault_doc = await vault_service.upload(
                user_id=user.user_id,
                filename=audio.filename or f"voice_{utc_now().timestamp()}.webm",
                content=audio_bytes,
                mime_type=mime_type,
                document_type="voice_recording",
                description="Voice recording kept as evidence",
                tags=["voice", "evidence"],
                source_module="voice",
                access_token=real_token,
                storage_provider=user.provider.value if user.provider else "local",
            )
            result["audio_vault_id"] = vault_doc.vault_id
        except Exception as exc:
            logger.warning("Could not store kept voice recording: %s", exc)
            result["audio_keep_error"] = "Transcribed, but the audio could not be saved as evidence."

    return result
