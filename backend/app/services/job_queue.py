"""
Asynchronous Job Queue Manager for Verifact Inference.
Tracks long-running radiograph triage jobs, progress updates, and completion results.
Thread-safe in-memory store with Redis-ready interface.
"""

import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import threading


class JobRecord:
    def __init__(self, job_id: str, user_id: int):
        self.job_id = job_id
        self.user_id = user_id
        self.status = "queued"  # queued, processing, completed, failed
        self.progress = 0       # 0 to 100
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "progress": self.progress,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class JobQueueManager:
    def __init__(self):
        self._jobs: Dict[str, JobRecord] = {}
        self._lock = threading.Lock()

    def create_job(self, job_id: str, user_id: int) -> JobRecord:
        with self._lock:
            record = JobRecord(job_id, user_id)
            self._jobs[job_id] = record
            return record

    def update_progress(self, job_id: str, progress: int, status: str = "processing"):
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].progress = min(100, max(0, progress))
                self._jobs[job_id].status = status
                self._jobs[job_id].updated_at = datetime.now(timezone.utc)

    def complete_job(self, job_id: str, result: Dict[str, Any]):
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].progress = 100
                self._jobs[job_id].status = "completed"
                self._jobs[job_id].result = result
                self._jobs[job_id].updated_at = datetime.now(timezone.utc)

    def fail_job(self, job_id: str, error_message: str):
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].status = "failed"
                self._jobs[job_id].error = error_message
                self._jobs[job_id].updated_at = datetime.now(timezone.utc)

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            rec = self._jobs.get(job_id)
            return rec.to_dict() if rec else None


_job_manager = JobQueueManager()


def get_job_manager() -> JobQueueManager:
    return _job_manager
