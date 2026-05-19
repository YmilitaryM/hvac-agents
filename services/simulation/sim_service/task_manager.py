"""Manage long-running simulation tasks with progress tracking.

Uses in-memory storage with optional sync Redis client for persistence.
"""
import time
import uuid
import json
from typing import Optional


class TaskManager:
    """Manage long-running simulation tasks with progress tracking."""

    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._tasks: dict[str, dict] = {}  # in-memory fallback

    def create_task(self, task_type: str, params: dict) -> str:
        """Create a new task and return task_id."""
        task_id = uuid.uuid4().hex[:16]
        task = {
            "task_id": task_id,
            "type": task_type,
            "status": "pending",
            "progress_pct": 0,
            "params": params,
            "result": None,
            "error": None,
            "created_at": time.time(),
            "completed_at": None,
        }
        self._tasks[task_id] = task
        if self._redis:
            try:
                self._redis.set(f"task:{task_id}", json.dumps(task))
            except Exception:
                pass
        return task_id

    def update_progress(self, task_id: str, progress_pct: float, status: str = "running"):
        task = self._tasks.get(task_id, {})
        task["progress_pct"] = progress_pct
        task["status"] = status
        if self._redis:
            try:
                self._redis.set(f"task:{task_id}", json.dumps(task))
            except Exception:
                pass

    def complete_task(self, task_id: str, result: dict):
        task = self._tasks.get(task_id, {})
        task["status"] = "completed"
        task["progress_pct"] = 100
        task["result"] = result
        task["completed_at"] = time.time()
        if self._redis:
            try:
                self._redis.set(f"task:{task_id}", json.dumps(task))
            except Exception:
                pass

    def fail_task(self, task_id: str, error: str):
        task = self._tasks.get(task_id, {})
        task["status"] = "failed"
        task["error"] = error
        task["completed_at"] = time.time()
        if self._redis:
            try:
                self._redis.set(f"task:{task_id}", json.dumps(task))
            except Exception:
                pass

    def get_task(self, task_id: str) -> Optional[dict]:
        if self._redis:
            try:
                data = self._redis.get(f"task:{task_id}")
                if data:
                    return json.loads(data)
            except Exception:
                pass
        return self._tasks.get(task_id)
