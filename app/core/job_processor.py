"""
Job Processor - Background Task Processing System
============================================

Handles asynchronous background jobs for document analysis and processing.
"""

import logging
import asyncio
from app.core.id_gen import make_id
from app.core.utc import utc_now
import json
import time
from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum
from collections import defaultdict, deque
import threading
import traceback

logger = logging.getLogger(__name__)

try:
    from sqlalchemy import select
    from app.core.database import get_db_session
    from app.models.models import DocumentPipelineIndex, DeepOCRStatus
    HAS_DB_INDEX = True
except Exception:
    HAS_DB_INDEX = False
    DocumentPipelineIndex = None  # type: ignore
    DeepOCRStatus = None  # type: ignore

class JobStatus(Enum):
    """Job status types."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"

class JobPriority(Enum):
    """Job priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

@dataclass
class Job:
    """Background job definition."""
    id: str
    type: str
    payload: Dict[str, Any]
    status: JobStatus = JobStatus.PENDING
    priority: JobPriority = JobPriority.NORMAL
    created_at: datetime = field(default_factory=lambda: utc_now())
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 300
    progress: float = 0.0
    user_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "status": self.status.value,
            "priority": self.priority.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "result": self.result,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
            "progress": self.progress,
            "user_id": self.user_id
        }

class JobQueue:
    """Priority-based job queue."""
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self._queues: Dict[JobPriority, deque] = {
            priority: deque() for priority in JobPriority
        }
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)
    
    def put(self, job: Job):
        """Add job to queue."""
        with self._lock:
            if len(self) >= self.max_size:
                # Remove oldest low priority job if needed
                self._remove_oldest_low_priority()
            
            self._queues[job.priority].append(job)
            self._not_empty.notify()
    
    def get(self, timeout: Optional[float] = None) -> Optional[Job]:
        """Get next job from queue."""
        with self._lock:
            # Wait for job to be available
            while self.is_empty():
                if not self._not_empty.wait(timeout):
                    return None
            
            # Get highest priority job
            for priority in sorted(JobPriority, key=lambda p: p.value, reverse=True):
                if self._queues[priority]:
                    return self._queues[priority].popleft()
            
            return None
    
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return all(len(queue) == 0 for queue in self._queues.values())
    
    def __len__(self) -> int:
        """Get total queue size."""
        return sum(len(queue) for queue in self._queues.values())
    
    def _remove_oldest_low_priority(self):
        """Remove oldest low priority job."""
        if self._queues[JobPriority.LOW]:
            self._queues[JobPriority.LOW].popleft()

class JobProcessor:
    """Background job processor."""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.job_queue = JobQueue()
        self.running_jobs: Dict[str, Job] = {}
        self.completed_jobs: Dict[str, Job] = {}
        self.job_handlers: Dict[str, Callable] = {}
        
        # Worker threads
        self.workers: List[threading.Thread] = []
        self.shutdown_event = threading.Event()
        
        # Statistics
        self.stats = {
            "jobs_processed": 0,
            "jobs_failed": 0,
            "jobs_cancelled": 0,
            "total_processing_time": 0.0,
            "average_processing_time": 0.0
        }
        
        # Job retention
        self.max_completed_jobs = 1000
        
    def register_handler(self, job_type: str, handler: Callable):
        """Register a job handler."""
        self.job_handlers[job_type] = handler
        logger.info(f"Registered job handler for type: {job_type}")
    
    def submit_job(self, job_type: str, payload: Dict[str, Any], 
                  priority: JobPriority = JobPriority.NORMAL,
                  user_id: str = None, **kwargs) -> str:
        """Submit a new job."""
        job_id = make_id("job")
        
        job = Job(
            id=job_id,
            type=job_type,
            payload=payload,
            priority=priority,
            user_id=user_id,
            **kwargs
        )
        
        self.job_queue.put(job)
        logger.info(f"Submitted job {job_id} of type {job_type}")
        
        return job_id
    
    def start(self):
        """Start the job processor."""
        if self.workers:
            return  # Already started
        
        # Start worker threads
        for i in range(self.max_workers):
            worker = threading.Thread(target=self._worker_loop, name=f"JobWorker-{i}")
            worker.daemon = True
            worker.start()
            self.workers.append(worker)
        
        logger.info(f"Started job processor with {self.max_workers} workers")
    
    def stop(self):
        """Stop the job processor."""
        self.shutdown_event.set()
        
        # Wait for workers to finish
        for worker in self.workers:
            worker.join(timeout=5)
        
        self.workers.clear()
        logger.info("Stopped job processor")
    
    def _worker_loop(self):
        """Worker thread main loop."""
        while not self.shutdown_event.is_set():
            try:
                # Get next job
                job = self.job_queue.get(timeout=1.0)
                if job is None:
                    continue
                
                # Process job
                self._process_job(job)
                
            except Exception as e:
                logger.error(f"Worker error: {e}")
    
    def _process_job(self, job: Job):
        """Process a single job."""
        job.status = JobStatus.RUNNING
        job.started_at = utc_now()
        self.running_jobs[job.id] = job
        
        start_time = time.time()
        
        # Send job started notification
        self._send_job_notification(job, "started")
        
        try:
            # Check if handler exists
            if job.type not in self.job_handlers:
                raise ValueError(f"No handler registered for job type: {job.type}")
            
            handler = self.job_handlers[job.type]
            
            # Execute job with timeout
            result = asyncio.run(self._execute_with_timeout(
                handler, job.payload, job.timeout_seconds
            ))
            
            # Mark as completed
            job.status = JobStatus.COMPLETED
            job.result = result
            job.progress = 100.0
            job.completed_at = utc_now()
            
            self.stats["jobs_processed"] += 1
            
            # Send job completed notification
            self._send_job_notification(job, "completed")
            
            logger.info(f"Completed job {job.id}")
            
        except Exception as e:
            job.error_message = str(e)
            job.completed_at = utc_now()
            
            # Check if should retry
            if job.retry_count < job.max_retries:
                job.status = JobStatus.RETRYING
                job.retry_count += 1
                
                # Send job retry notification
                self._send_job_notification(job, "retrying")
                
                # Re-queue with delay
                def retry_job():
                    time.sleep(min(60, job.retry_count * 10))  # Exponential backoff
                    job.status = JobStatus.PENDING
                    job.started_at = None
                    job.completed_at = None
                    self.job_queue.put(job)
                
                retry_thread = threading.Thread(target=retry_job)
                retry_thread.daemon = True
                retry_thread.start()
                
                logger.warning(f"Retrying job {job.id} (attempt {job.retry_count})")
            else:
                job.status = JobStatus.FAILED
                self.stats["jobs_failed"] += 1
                
                # Send job failed notification
                self._send_job_notification(job, "failed")
                
                logger.error(f"Failed job {job.id}: {e}")
        
        finally:
            # Update statistics
            processing_time = time.time() - start_time
            self.stats["total_processing_time"] += processing_time
            self.stats["average_processing_time"] = (
                self.stats["total_processing_time"] / self.stats["jobs_processed"]
                if self.stats["jobs_processed"] > 0 else 0
            )
            
            # Move to completed jobs
            if job.id in self.running_jobs:
                del self.running_jobs[job.id]
            
            self.completed_jobs[job.id] = job
            
            # Clean up old completed jobs
            self._cleanup_completed_jobs()
    
    def _send_job_notification(self, job: Job, status: str):
        """Send real-time job status notification via WebSocket."""
        try:
            from app.core.websocket_manager import get_websocket_manager
            
            ws_manager = get_websocket_manager()
            
            # Create notification data
            notification_data = {
                "job_id": job.id,
                "type": job.type,
                "status": status,
                "progress": job.progress,
                "error_message": job.error_message,
                "result": job.result,
                "retry_count": job.retry_count,
                "max_retries": job.max_retries,
                "created_at": job.created_at.isoformat(),
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None
            }
            
            # Send to user if user_id is available
            if job.user_id:
                asyncio.run(ws_manager.send_job_status_update(
                    user_id=job.user_id,
                    job_id=job.id,
                    status=status,
                    progress=job.progress,
                    result=job.result
                ))
            
            # Also broadcast to job monitoring subscription
            asyncio.run(ws_manager.broadcast_to_subscription(
                "job_monitoring",
                WebSocketMessage(
                    type="job_update",
                    data=notification_data,
                    timestamp=utc_now()
                )
            ))
            
        except Exception as e:
            logger.error(f"Failed to send job notification: {e}")
    
    async def _execute_with_timeout(self, handler: Callable, payload: Dict[str, Any], 
                                  timeout_seconds: int) -> Any:
        """Execute handler with timeout."""
        try:
            if asyncio.iscoroutinefunction(handler):
                return await asyncio.wait_for(handler(payload), timeout=timeout_seconds)
            else:
                # Run synchronous function in thread pool
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, handler, payload)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Job timed out after {timeout_seconds} seconds")
    
    def _cleanup_completed_jobs(self):
        """Clean up old completed jobs."""
        if len(self.completed_jobs) > self.max_completed_jobs:
            # Remove oldest jobs
            sorted_jobs = sorted(
                self.completed_jobs.items(),
                key=lambda x: x[1].completed_at or x[1].created_at
            )
            
            jobs_to_remove = len(self.completed_jobs) - self.max_completed_jobs
            for job_id, _ in sorted_jobs[:jobs_to_remove]:
                del self.completed_jobs[job_id]
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status."""
        # Check running jobs
        if job_id in self.running_jobs:
            return self.running_jobs[job_id].to_dict()
        
        # Check completed jobs
        if job_id in self.completed_jobs:
            return self.completed_jobs[job_id].to_dict()
        
        # Check queue
        for queue in self.job_queue._queues.values():
            for job in queue:
                if job.id == job_id:
                    return job.to_dict()
        
        return None
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job."""
        # Remove from queue if pending
        for queue in self.job_queue._queues.values():
            for i, job in enumerate(queue):
                if job.id == job_id and job.status == JobStatus.PENDING:
                    job.status = JobStatus.CANCELLED
                    del queue[i]
                    self.completed_jobs[job_id] = job
                    self.stats["jobs_cancelled"] += 1
                    return True
        
        # Cannot cancel running jobs (would need interrupt mechanism)
        return False
    
    def get_user_jobs(self, user_id: str, status: Optional[JobStatus] = None) -> List[Dict[str, Any]]:
        """Get jobs for a specific user."""
        user_jobs = []
        
        # Check running jobs
        for job in self.running_jobs.values():
            if job.user_id == user_id and (status is None or job.status == status):
                user_jobs.append(job.to_dict())
        
        # Check completed jobs
        for job in self.completed_jobs.values():
            if job.user_id == user_id and (status is None or job.status == status):
                user_jobs.append(job.to_dict())
        
        return sorted(user_jobs, key=lambda x: x["created_at"], reverse=True)
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        queue_sizes = {
            priority.name.lower(): len(queue)
            for priority, queue in self.job_queue._queues.items()
        }
        
        return {
            "total_pending": sum(queue_sizes.values()),
            "by_priority": queue_sizes,
            "running": len(self.running_jobs),
            "completed": len(self.completed_jobs),
            "workers": len(self.workers),
            "stats": self.stats.copy()
        }
    
    def update_job_progress(self, job_id: str, progress: float, message: str = None):
        """Update job progress."""
        if job_id in self.running_jobs:
            job = self.running_jobs[job_id]
            job.progress = min(100.0, max(0.0, progress))
            
            if message:
                job.result = job.result or {}
                job.result["progress_message"] = message

# Global job processor instance
_job_processor: Optional[JobProcessor] = None

def get_job_processor() -> JobProcessor:
    """Get the global job processor instance."""
    global _job_processor
    
    if _job_processor is None:
        _job_processor = JobProcessor(max_workers=4)
        _job_processor.start()
        
        # Register default handlers
        register_default_handlers(_job_processor)
    
    return _job_processor

def register_default_handlers(processor: JobProcessor):
    """Register default job handlers."""
    
    async def document_analysis_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle document analysis job."""
        document_id = payload.get("document_id")
        analysis_type = payload.get("analysis_type", "basic")
        
        logger.info(f"Starting document analysis for {document_id}")
        
        # Simulate analysis work
        await asyncio.sleep(2)
        
        # Update progress
        processor.update_job_progress(payload.get("job_id"), 25, "Extracting text...")
        await asyncio.sleep(1)
        
        processor.update_job_progress(payload.get("job_id"), 50, "Analyzing content...")
        await asyncio.sleep(1)
        
        processor.update_job_progress(payload.get("job_id"), 75, "Generating insights...")
        await asyncio.sleep(1)
        
        processor.update_job_progress(payload.get("job_id"), 100, "Analysis complete")
        
        return {
            "document_id": document_id,
            "analysis_type": analysis_type,
            "results": {
                "pages": 10,
                "word_count": 5000,
                "language": "en",
                "confidence": 0.95
            }
        }
    
    async def thumbnail_generation_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle thumbnail generation job."""
        document_id = payload.get("document_id")
        page_numbers = payload.get("page_numbers", [1])
        
        logger.info(f"Generating thumbnails for {document_id}")
        
        # Simulate thumbnail generation
        await asyncio.sleep(1)
        
        return {
            "document_id": document_id,
            "thumbnails": [
                {
                    "page": page,
                    "url": f"/thumbnails/{document_id}/page_{page}.jpg",
                    "size": "200x300"
                }
                for page in page_numbers
            ]
        }
    
    async def document_indexing_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle document indexing job."""
        document_id = payload.get("document_id")
        content = payload.get("content", "")
        
        logger.info(f"Indexing document {document_id}")
        
        # Simulate indexing
        await asyncio.sleep(0.5)
        
        return {
            "document_id": document_id,
            "indexed_words": len(content.split()),
            "keywords": ["housing", "tenant", "rights"][:10],
            "indexed_at": utc_now().isoformat()
        }
    
    async def deep_ocr_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Deep OCR pass-2 job.

        Picks up documents in `pending` status and flips `deep_ocr_status` to
        `processing`, runs the Semantic Context Engine on the raw OCR text produced
        by Pass 1, then marks `deep_ocr_status` `complete` or `failed`.
        """
        doc_id = payload.get("doc_id")
        user_id = payload.get("user_id")
        vault_id = payload.get("vault_id")

        if not doc_id or not user_id:
            raise ValueError("deep_ocr payload must include doc_id and user_id")

        if not HAS_DB_INDEX:
            return {"status": "skipped", "reason": "db_index_unavailable"}

        # Upsert pipeline index row and mark as processing.
        async with get_db_session() as db:
            result = await db.execute(
                select(DocumentPipelineIndex).where(DocumentPipelineIndex.doc_id == doc_id)  # type: ignore[arg-type]
            )
            row = result.scalar_one_or_none()
            if row is None:
                row = DocumentPipelineIndex(
                    doc_id=doc_id,
                    user_id=user_id,
                    payload_json=json.dumps({"vault_id": vault_id, "queued_at": utc_now().isoformat()}),
                    deep_ocr_status=DeepOCRStatus.PENDING.value,  # type: ignore[union-attr]
                )
                db.add(row)
                await db.commit()
            row.deep_ocr_status = DeepOCRStatus.PROCESSING.value  # type: ignore[union-attr]
            row.updated_at = utc_now()
            await db.commit()

        logger.info(f"Deep OCR processing started for doc {doc_id}")

        # Run the Semantic Context Engine on Pass 1 raw OCR text.
        pass2_status = DeepOCRStatus.COMPLETE.value  # type: ignore[union-attr]
        pass2_results: list[dict[str, Any]] = []
        pass2_error: Optional[str] = None
        overlay_id: Optional[str] = None

        try:
            from app.services.document_intake import get_intake_engine
            from app.services.semantic_context_engine import SemanticContextEngine

            engine = get_intake_engine()
            doc = engine.get_document(doc_id)
            if doc is None:
                raise ValueError(f"IntakeDocument {doc_id} not found")

            raw_text = None
            if doc.extraction and doc.extraction.full_text:
                raw_text = doc.extraction.full_text

            if not raw_text:
                # Pass 1 has not produced text; cannot run Pass 2.
                pass2_status = DeepOCRStatus.NEEDS_REPROCESS.value  # type: ignore[union-attr]
                pass2_error = "Pass 1 raw OCR text not available"
            else:
                doc_type = doc.doc_type.value if doc.doc_type else None
                # Run CPU-bound regex work off the event loop thread.
                results = await asyncio.to_thread(
                    SemanticContextEngine().extract, raw_text, doc_type
                )
                pass2_results = [r.to_dict() for r in results]

                # Write structured Pass 2 results to the user's cloud overlays so the
                # Document Center can read real data instead of processing_incomplete.
                try:
                    from app.core.oauth_token_manager import get_valid_token_for_user
                    from app.core.user_id import get_provider_from_user_id
                    from app.core.overlay_types import OverlayType
                    from app.models.unified_overlay_models import CreateOverlayRequest
                    from app.services.storage import get_provider
                    from app.services.unified_overlay_manager import UnifiedOverlayManager

                    provider_code = get_provider_from_user_id(user_id) or getattr(
                        doc, "storage_provider", None
                    )
                    if not provider_code or provider_code == "local":
                        logger.info(
                            "Skipping overlay write for doc %s (provider=%s)",
                            doc_id,
                            provider_code or "unknown",
                        )
                    else:
                        access_token = get_valid_token_for_user(user_id)
                        if not access_token:
                            raise RuntimeError("No valid access token for overlay creation")

                        storage = get_provider(provider_code, access_token=access_token)
                        manager = UnifiedOverlayManager(storage, user_id)

                        # Document Center queries overlays by safe_filename (vault_id.ext).
                        if vault_id and doc.filename:
                            ext = (
                                doc.filename.rsplit(".", 1)[-1].lower()
                                if "." in doc.filename
                                else "bin"
                            )
                            safe_filename = f"{vault_id}.{ext}"
                        else:
                            safe_filename = doc.id

                        vault_path = getattr(doc, "storage_path", None) or vault_id or ""

                        formatted_dates = [
                            f"{r.get('raw_text', '')} — {r.get('semantic_label', 'date')}"
                            + (f" ({r.get('trigger_phrase', '')})" if r.get("trigger_phrase") else "")
                            for r in pass2_results
                        ]

                        payload = {
                            "text": raw_text,
                            "dates": formatted_dates,
                            "semantic_dates": pass2_results,
                            "parties": [],
                            "amounts": [],
                            "key_terms": [],
                            "source": "deep_ocr_pass2",
                        }

                        overlay_resp = await manager.create_overlay(
                            CreateOverlayRequest(
                                overlay_type=OverlayType.DOCUMENT_EXTRACTION,
                                document_id=safe_filename,
                                vault_path=vault_path,
                                payload=payload,
                                metadata={
                                    "doc_id": doc_id,
                                    "vault_id": vault_id,
                                    "processed_at": utc_now().isoformat(),
                                    "engine": "SemanticContextEngine",
                                },
                                ephemeral=False,
                            )
                        )
                        if overlay_resp.success:
                            overlay_id = overlay_resp.overlay_id
                            logger.info(
                                "Deep OCR overlay created for doc %s: %s",
                                doc_id,
                                overlay_id,
                            )
                        else:
                            raise RuntimeError(
                                f"Overlay creation failed: {overlay_resp.message}"
                            )
                except Exception as exc:
                    logger.exception("Deep OCR overlay creation failed for doc %s", doc_id)
                    pass2_status = DeepOCRStatus.FAILED.value  # type: ignore[union-attr]
                    pass2_error = str(exc)

        except Exception as exc:
            logger.exception("Deep OCR Pass 2 failed for doc %s", doc_id)
            pass2_status = DeepOCRStatus.FAILED.value  # type: ignore[union-attr]
            pass2_error = str(exc)

        # Persist Pass 2 results and final status.
        async with get_db_session() as db:
            result = await db.execute(
                select(DocumentPipelineIndex).where(DocumentPipelineIndex.doc_id == doc_id)  # type: ignore[arg-type]
            )
            row = result.scalar_one_or_none()
            if row is not None:
                payload = json.loads(row.payload_json or "{}")
                payload["pass2_results"] = pass2_results
                payload["completed_at"] = utc_now().isoformat()
                if overlay_id:
                    payload["overlay_id"] = overlay_id
                if pass2_error:
                    payload["pass2_error"] = pass2_error
                row.payload_json = json.dumps(payload)
                row.deep_ocr_status = pass2_status
                row.updated_at = utc_now()
                await db.commit()

            # Also mirror status onto the canonical Document row if one exists.
            try:
                from app.models.models import Document

                doc_result = await db.execute(select(Document).where(Document.id == doc_id))  # type: ignore[arg-type]
                canonical = doc_result.scalar_one_or_none()
                if canonical is not None:
                    canonical.deep_ocr_status = pass2_status  # type: ignore[union-attr]
                    await db.commit()
            except Exception:
                logger.debug("Could not mirror deep_ocr_status to Document %s", doc_id)

        return {
            "doc_id": doc_id,
            "vault_id": vault_id,
            "status": pass2_status,
            "pass2_results": pass2_results,
            "overlay_id": overlay_id,
            "error": pass2_error,
        }

    # Register handlers
    processor.register_handler("document_analysis", document_analysis_handler)
    processor.register_handler("thumbnail_generation", thumbnail_generation_handler)
    processor.register_handler("document_indexing", document_indexing_handler)
    processor.register_handler("deep_ocr", deep_ocr_handler)

# Helper functions
def submit_document_analysis_job(document_id: str, analysis_type: str = "basic", 
                                user_id: str = None) -> str:
    """Submit document analysis job."""
    processor = get_job_processor()
    return processor.submit_job(
        job_type="document_analysis",
        payload={
            "document_id": document_id,
            "analysis_type": analysis_type,
            "job_id": make_id("job")  # Will be overridden
        },
        priority=JobPriority.NORMAL,
        user_id=user_id
    )

def submit_deep_ocr_job(doc_id: str, user_id: str, vault_id: Optional[str] = None,
                        priority: JobPriority = JobPriority.NORMAL,
                        payload: Optional[Dict[str, Any]] = None) -> str:
    """Submit a Deep OCR pass-2 job for the given intake document."""
    processor = get_job_processor()
    payload = payload or {}
    payload.update({"doc_id": doc_id, "user_id": user_id, "vault_id": vault_id})
    return processor.submit_job(
        job_type="deep_ocr",
        payload=payload,
        priority=priority,
        user_id=user_id,
    )


def submit_thumbnail_generation_job(document_id: str, page_numbers: List[int] = None,
                                   user_id: str = None) -> str:
    """Submit thumbnail generation job."""
    processor = get_job_processor()
    return processor.submit_job(
        job_type="thumbnail_generation",
        payload={
            "document_id": document_id,
            "page_numbers": page_numbers or [1]
        },
        priority=JobPriority.LOW,
        user_id=user_id
    )

def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Get job status."""
    processor = get_job_processor()
    return processor.get_job_status(job_id)

def get_user_jobs(user_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get user's jobs."""
    processor = get_job_processor()
    job_status = JobStatus(status) if status else None
    return processor.get_user_jobs(user_id, job_status)

def get_job_queue_stats() -> Dict[str, Any]:
    """Get job queue statistics."""
    processor = get_job_processor()
    return processor.get_queue_stats()

# Cleanup on shutdown
import atexit
atexit.register(lambda: get_job_processor().stop())
