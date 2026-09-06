"""Voice module registration - FunctionGroupContracts.

Server-side voice-to-text fallback behind /api/voice. The Web Speech API is
the default; this router handles browsers where it is unavailable or
unsuitable. Audio content is tenant data.
"""

from app.core.module_contracts import FunctionGroupContract, register_function_group

register_function_group(
    FunctionGroupContract(
        module="voice",
        group_name="voice_transcribe",
        title="Voice Transcribe (SSOT)",
        description=(
            "CANONICAL server-side transcription fallback for voice input. "
            "Used only when the Web Speech API is unavailable."
        ),
        inputs=("audio", "user_id?"),
        outputs=("transcript",),
        dependencies=("app.modules.voice.router",),
        deterministic=False,
        tier="T2",
        allowed_routes=("/api/voice/transcribe",),
        allowed_prefixes=("/api/voice",),
    )
)
