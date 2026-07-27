"""
Voice transcription service.

Default path: Web Speech API runs entirely in the browser. No server call.
Fallback path: browser records audio and POSTs it to /api/voice/transcribe.
This service sends the audio to OpenAI's Whisper API and immediately discards
the raw bytes. A caller may choose to store the audio as evidence separately.
"""

import io
import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_MIME_MAP = {
    "webm": "audio/webm",
    "mp3": "audio/mpeg",
    "mp4": "audio/mp4",
    "m4a": "audio/m4a",
    "wav": "audio/wav",
    "ogg": "audio/ogg",
}


async def transcribe_audio(
    audio_bytes: bytes,
    filename: str = "audio.webm",
    language: str | None = None,
) -> dict:
    """
    Transcribe audio bytes using OpenAI Whisper.

    Args:
        audio_bytes: Raw audio file content.
        filename: Original filename; used to guess MIME type for Whisper.
        language: Optional BCP-47 language code (e.g. 'en', 'es', 'so').

    Returns:
        Dict with keys: success, transcript, source, message, language.
        The raw audio is not retained by this function.
    """
    if not audio_bytes:
        return {
            "success": False,
            "transcript": "",
            "source": "none",
            "message": "Empty audio file.",
            "language": language or "auto",
        }

    settings = get_settings()
    api_key = settings.openai_api_key
    if not api_key:
        logger.warning("OPENAI_API_KEY not configured; Whisper fallback unavailable")
        return {
            "success": False,
            "transcript": "",
            "source": "none",
            "message": "Whisper fallback is not configured on this server. Please type your note.",
            "language": language or "auto",
        }

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "webm"
    content_type = _MIME_MAP.get(ext, "audio/webm")

    data = {"model": "whisper-1"}
    if language:
        data["language"] = language

    url = "https://api.openai.com/v1/audio/transcriptions"
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                data=data,
                files={
                    "file": (filename, io.BytesIO(audio_bytes), content_type),
                },
            )
            response.raise_for_status()
            payload = response.json()
            transcript = payload.get("text", "").strip()
            return {
                "success": True,
                "transcript": transcript,
                "source": "whisper",
                "message": "",
                "language": language or "auto",
            }
    except httpx.HTTPStatusError as exc:
        logger.error("Whisper API HTTP error: %s - %s", exc.response.status_code, exc.response.text)
        return {
            "success": False,
            "transcript": "",
            "source": "whisper",
            "message": f"Transcription service returned an error ({exc.response.status_code}). Please type your note.",
            "language": language or "auto",
        }
    except Exception:
        logger.exception("Whisper transcription failed")
        return {
            "success": False,
            "transcript": "",
            "source": "whisper",
            "message": "Transcription failed. Please type your note.",
            "language": language or "auto",
        }
