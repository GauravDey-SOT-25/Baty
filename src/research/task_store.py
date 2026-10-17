"""In-memory and file-backed task and monitor store.

Provides CRUD for ResearchTaskRecord and MonitorRecord objects.
Persists to local JSON files so tasks survive server restarts.

The store API is designed to match what Firestore calls would look like,
so it can be replaced by a Firebase backend without changing callers.

Thread-safety: all mutations acquire a per-collection lock.
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.research.provider import MonitorRecord, ResearchTaskRecord

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("CYBER_DATA_PATH", ROOT / "data"))

_TASKS_FILE = DATA_DIR / "research_tasks.json"
_MONITORS_FILE = DATA_DIR / "research_monitors.json"

_task_lock = threading.Lock()
_monitor_lock = threading.Lock()

# In-memory caches — loaded lazily
_tasks: dict[str, dict] | None = None
_monitors: dict[str, dict] | None = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_tasks() -> dict[str, dict]:
    global _tasks
    if _tasks is not None:
        return _tasks
    try:
        if _TASKS_FILE.exists():
            _restrict_file_permissions(_TASKS_FILE)
            raw = _TASKS_FILE.read_text(encoding="utf-8")
            _tasks = json.loads(raw)
        else:
            _tasks = {}
    except (json.JSONDecodeError, OSError):
        _tasks = {}
    return _tasks


def _save_tasks(data: dict[str, dict]) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _atomic_private_json_write(_TASKS_FILE, data)
    except OSError:
        pass  # Persistence failure is non-fatal; in-memory state remains


def _load_monitors() -> dict[str, dict]:
    global _monitors
    if _monitors is not None:
        return _monitors
    try:
        if _MONITORS_FILE.exists():
            _restrict_file_permissions(_MONITORS_FILE)
            raw = _MONITORS_FILE.read_text(encoding="utf-8")
            _monitors = json.loads(raw)
        else:
            _monitors = {}
    except (json.JSONDecodeError, OSError):
        _monitors = {}
    return _monitors


def _save_monitors(data: dict[str, dict]) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _atomic_private_json_write(_MONITORS_FILE, data)
    except OSError:
        pass


def _atomic_private_json_write(path: Path, data: dict) -> None:
    """Atomically persist research data with owner-only file permissions."""
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=DATA_DIR)
    temp_path = Path(temp_name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        os.chmod(path, 0o600)
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass


def _restrict_file_permissions(path: Path) -> None:
    """Tighten existing research files when the process can do so."""
    try:
        os.chmod(path, 0o600)
    except OSError:
        # Some filesystems do not support POSIX modes. Keep data accessible
        # locally, while documenting the platform-dependent guarantee.
        pass


# ---------------------------------------------------------------------------
# Task store operations
# ---------------------------------------------------------------------------

def create_task(question: str, provider: str, processor: str = "pro",
                owner_uid: Optional[str] = None) -> ResearchTaskRecord:
    """Create and persist a new research task in 'pending' state."""
    task_id = "task_" + uuid.uuid4().hex
    record = ResearchTaskRecord(
        task_id=task_id,
        question=question,
        status="pending",
        provider=provider,
        processor=processor,
        owner_uid=owner_uid,
    )
    with _task_lock:
        data = _load_tasks()
        data[task_id] = record.to_dict()
        _save_tasks(data)
    return record


def get_task(task_id: str) -> Optional[ResearchTaskRecord]:
    """Retrieve a task by ID, or None if not found."""
    with _task_lock:
        data = _load_tasks()
        raw = data.get(task_id)
    if raw is None:
        return None
    return _dict_to_task(raw)


def update_task(record: ResearchTaskRecord) -> None:
    """Persist updated task state."""
    record.updated_at = _now()
    with _task_lock:
        data = _load_tasks()
        data[record.task_id] = record.to_dict()
        _save_tasks(data)


def list_tasks(owner_uid: Optional[str] = None, limit: int = 50) -> list[ResearchTaskRecord]:
    """List tasks, optionally filtered by owner. Newest first."""
    with _task_lock:
        data = _load_tasks()
    records = [_dict_to_task(v) for v in data.values()]
    if owner_uid is not None:
        records = [r for r in records if r.owner_uid == owner_uid]
    records.sort(key=lambda r: r.created_at, reverse=True)
    return records[:limit]


def _dict_to_task(raw: dict) -> ResearchTaskRecord:
    return ResearchTaskRecord(
        task_id=raw.get("task_id", ""),
        question=raw.get("question", ""),
        status=raw.get("status", "pending"),
        provider=raw.get("provider", "unknown"),
        provider_run_id=raw.get("provider_run_id"),
        processor=raw.get("processor", "pro"),
        created_at=raw.get("created_at", ""),
        updated_at=raw.get("updated_at", ""),
        completed_at=raw.get("completed_at"),
        owner_uid=raw.get("owner_uid"),
        error_message=raw.get("error_message"),
        result=raw.get("result"),
    )


# ---------------------------------------------------------------------------
# Monitor store operations
# ---------------------------------------------------------------------------

def create_monitor(query: str, provider: str,
                   owner_uid: Optional[str] = None) -> MonitorRecord:
    """Create and persist a new monitor in 'active' state."""
    monitor_id = "monitor_" + uuid.uuid4().hex
    record = MonitorRecord(
        monitor_id=monitor_id,
        query=query,
        status="active",
        provider=provider,
        owner_uid=owner_uid,
    )
    with _monitor_lock:
        data = _load_monitors()
        data[monitor_id] = record.to_dict()
        _save_monitors(data)
    return record


def get_monitor(monitor_id: str) -> Optional[MonitorRecord]:
    """Retrieve a monitor by ID, or None if not found."""
    with _monitor_lock:
        data = _load_monitors()
        raw = data.get(monitor_id)
    if raw is None:
        return None
    return _dict_to_monitor(raw)


def update_monitor(record: MonitorRecord) -> None:
    """Persist updated monitor state."""
    record.updated_at = _now()
    with _monitor_lock:
        data = _load_monitors()
        data[record.monitor_id] = record.to_dict()
        _save_monitors(data)


def delete_monitor(monitor_id: str) -> bool:
    """Mark a monitor as deleted. Returns True if it existed."""
    with _monitor_lock:
        data = _load_monitors()
        if monitor_id not in data:
            return False
        data[monitor_id]["status"] = "deleted"
        data[monitor_id]["updated_at"] = _now()
        _save_monitors(data)
    return True


def list_monitors(owner_uid: Optional[str] = None, include_deleted: bool = False,
                  limit: int = 50) -> list[MonitorRecord]:
    """List monitors, optionally filtered by owner. Newest first."""
    with _monitor_lock:
        data = _load_monitors()
    records = [_dict_to_monitor(v) for v in data.values()]
    if not include_deleted:
        records = [r for r in records if r.status != "deleted"]
    if owner_uid is not None:
        records = [r for r in records if r.owner_uid == owner_uid]
    records.sort(key=lambda r: r.created_at, reverse=True)
    return records[:limit]


def append_monitor_finding(monitor_id: str, finding: dict) -> bool:
    """Append a new finding to a monitor's findings list (max 20)."""
    with _monitor_lock:
        data = _load_monitors()
        if monitor_id not in data:
            return False
        findings = data[monitor_id].get("findings", [])
        findings.append(finding)
        data[monitor_id]["findings"] = findings[-20:]
        data[monitor_id]["last_event_at"] = _now()
        data[monitor_id]["updated_at"] = _now()
        _save_monitors(data)
    return True


def _dict_to_monitor(raw: dict) -> MonitorRecord:
    return MonitorRecord(
        monitor_id=raw.get("monitor_id", ""),
        query=raw.get("query", ""),
        status=raw.get("status", "active"),
        provider=raw.get("provider", "unknown"),
        provider_monitor_id=raw.get("provider_monitor_id"),
        created_at=raw.get("created_at", ""),
        updated_at=raw.get("updated_at", ""),
        last_checked_at=raw.get("last_checked_at"),
        last_event_at=raw.get("last_event_at"),
        owner_uid=raw.get("owner_uid"),
        error_message=raw.get("error_message"),
        findings=raw.get("findings", []),
    )
