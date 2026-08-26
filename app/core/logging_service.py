"""Buffered, structured logging with async R2/local flush and live tail.

Logs are buffered in memory, flushed periodically to R2 or local disk as NDJSON,
and kept for a configurable retention window (default 90 days). A live tail
endpoint can read the in-memory buffer. Runtime log-level changes are supported.

No user PII is intentionally logged by this service; the handler receives whatever
upstream log records emit.
"""

import asyncio
import json
import logging
import shutil
import socket
import threading
from collections import deque
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.utc import utc_now

logger = logging.getLogger("semptify.logging_service")

DEFAULT_BUFFER_SIZE = 10_000
DEFAULT_FLUSH_INTERVAL_SECONDS = 60

_log_buffer: "LogBuffer | None" = None
_log_flusher: "LogFlusher | None" = None


def _make_log_entry(record: logging.LogRecord) -> dict[str, Any]:
    """Convert a LogRecord into a structured dict aligned with JSONFormatter."""
    entry = {
        "timestamp": utc_now().isoformat(),
        "level": record.levelname,
        "logger": record.name,
        "message": record.getMessage(),
        "module": record.module,
        "function": record.funcName,
        "line": record.lineno,
    }

    if record.exc_info:
        entry["exception"] = logging.Formatter().formatException(record.exc_info)

    for key in [
        "request_id",
        "user_id",
        "path",
        "method",
        "status_code",
        "duration_ms",
        "error_code",
        "client_ip",
    ]:
        if hasattr(record, key):
            entry[key] = getattr(record, key)

    # Any additional extras not already captured
    for key, value in record.__dict__.items():
        if (
            key
            not in {
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "exc_info",
                "exc_text",
                "thread",
                "threadName",
                "message",
                "taskName",
            }
            and not key.startswith("_")
            and key not in entry
        ):
            entry[key] = value

    return entry


class LogBuffer:
    """Thread-safe in-memory ring buffer for structured log entries."""

    def __init__(self, max_size: int = DEFAULT_BUFFER_SIZE):
        self._deque: deque[dict[str, Any]] = deque(maxlen=max_size)
        self._lock = threading.Lock()

    def append(self, entry: dict[str, Any]) -> None:
        with self._lock:
            self._deque.append(entry)

    def drain(self) -> list[dict[str, Any]]:
        """Return and clear all buffered entries."""
        with self._lock:
            entries = list(self._deque)
            self._deque.clear()
            return entries

    def tail(self, n: int) -> list[dict[str, Any]]:
        """Return the last n entries without removing them."""
        with self._lock:
            return list(self._deque)[-n:] if n > 0 else list(self._deque)


class BufferingHandler(logging.Handler):
    """Handler that copies structured log entries into a LogBuffer."""

    def __init__(self, buffer: LogBuffer):
        super().__init__()
        self.buffer = buffer

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.buffer.append(_make_log_entry(record))
        except Exception:
            self.handleError(record)


class LogFlusher:
    """Async background flusher: in-memory buffer -> R2 or local disk."""

    def __init__(
        self,
        buffer: LogBuffer,
        interval: int = DEFAULT_FLUSH_INTERVAL_SECONDS,
        retention_days: int = 90,
    ):
        self.buffer = buffer
        self.interval = interval
        self.retention_days = retention_days
        self._task: asyncio.Task | None = None
        self._running = False
        self._r2_provider: Any | None = None
        self._local_dir = Path("logs/archive")
        self._local_dir.mkdir(parents=True, exist_ok=True)

    def _settings(self):
        return get_settings()

    async def _get_r2(self) -> Any | None:
        if self._r2_provider:
            return self._r2_provider

        settings = self._settings()
        if not all(
            [
                settings.r2_account_id,
                settings.r2_access_key_id,
                settings.r2_secret_access_key,
                settings.r2_bucket_name,
            ]
        ):
            return None

        try:
            from app.services.storage.r2 import R2Provider
        except ImportError:
            return None

        self._r2_provider = R2Provider(
            account_id=settings.r2_account_id,
            access_key_id=settings.r2_access_key_id,
            secret_access_key=settings.r2_secret_access_key,
            bucket_name=settings.r2_bucket_name,
        )
        if await self._r2_provider.is_connected():
            return self._r2_provider

        logger.warning("R2 configured but unreachable; falling back to local log files")
        self._r2_provider = None
        return None

    async def _flush(self) -> None:
        entries = self.buffer.drain()
        if not entries:
            return

        payload = "".join(json.dumps(entry, default=str) + "\n" for entry in entries).encode("utf-8")
        timestamp = utc_now().strftime("%Y%m%d-%H%M%S-%f")
        hostname = socket.gethostname()

        r2 = await self._get_r2()
        if r2:
            settings = self._settings()
            prefix = settings.r2_logs_prefix.strip("/")
            key = f"{prefix}/{hostname}/{timestamp}.jsonl"
            await r2.upload_file(
                file_content=payload,
                destination_path="",
                filename=key,
                mime_type="application/x-ndjson",
            )
        else:
            date_dir = self._local_dir / utc_now().strftime("%Y-%m-%d")
            date_dir.mkdir(parents=True, exist_ok=True)
            (date_dir / f"{hostname}_{timestamp}.jsonl").write_bytes(payload)

    async def _cleanup(self) -> None:
        cutoff = utc_now() - timedelta(days=self.retention_days)

        r2 = await self._get_r2()
        if r2:
            settings = self._settings()
            prefix = settings.r2_logs_prefix.strip("/") + "/"
            try:
                files = await r2.list_files(prefix, recursive=True)
                for f in files:
                    modified = getattr(f, "modified_at", None)
                    if modified and modified < cutoff:
                        await r2.delete_file(f.path)
            except Exception as exc:
                logger.warning("R2 retention cleanup failed: %s", exc)
        else:
            for date_dir in self._local_dir.iterdir():
                if not date_dir.is_dir():
                    continue
                try:
                    dir_date = datetime.strptime(date_dir.name, "%Y-%m-%d").replace(tzinfo=UTC)
                except ValueError:
                    continue
                if dir_date < cutoff:
                    shutil.rmtree(date_dir, ignore_errors=True)

    async def _loop(self) -> None:
        while self._running:
            await asyncio.sleep(self.interval)
            try:
                await self._flush()
                await self._cleanup()
            except Exception as exc:
                logger.error("Log flush/cleanup failed: %s", exc)

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Log flusher started (interval=%ss, retention=%sd)", self.interval, self.retention_days)

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        try:
            await self._flush()
        except Exception as exc:
            logger.error("Final log flush failed: %s", exc)


def setup_application_logging(
    level: str,
    json_format: bool,
    log_file: Path | None,
    flush_interval: int = DEFAULT_FLUSH_INTERVAL_SECONDS,
    retention_days: int = 90,
) -> tuple[LogBuffer, LogFlusher]:
    """Configure root logging, add buffered handler, and create the flusher."""
    from app.core.logging_config import setup_logging as _base_setup

    _base_setup(level=level, json_format=json_format, log_file=str(log_file) if log_file else None)

    global _log_buffer, _log_flusher
    _log_buffer = LogBuffer()
    _log_flusher = LogFlusher(
        buffer=_log_buffer,
        interval=flush_interval,
        retention_days=retention_days,
    )

    handler = BufferingHandler(_log_buffer)
    root = logging.getLogger()
    root.addHandler(handler)

    return _log_buffer, _log_flusher


def get_log_buffer() -> LogBuffer | None:
    return _log_buffer


def get_log_flusher() -> LogFlusher | None:
    return _log_flusher


def get_log_tail(n: int = 100) -> list[dict[str, Any]]:
    """Return the last n buffered log entries."""
    if _log_buffer is None:
        return []
    return _log_buffer.tail(n)


def set_log_level(level: str) -> str:
    """Set the root logger and all handler levels at runtime."""
    level_upper = level.upper()
    numeric = getattr(logging, level_upper, logging.INFO)
    root = logging.getLogger()
    root.setLevel(numeric)
    for handler in root.handlers:
        handler.setLevel(numeric)
    return level_upper
