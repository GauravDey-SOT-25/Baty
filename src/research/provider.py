"""Provider abstraction for the research subsystem.

Defines the shared result schemas and the abstract ResearchProvider interface.
All provider implementations (Parallel, LocalFallback) must conform to this contract.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# Shared result schemas
# ---------------------------------------------------------------------------

@dataclass
class SearchExcerpt:
    """A single retrieved text excerpt from a search result."""
    text: str
    char_count: int = 0

    def __post_init__(self):
        self.char_count = len(self.text)


@dataclass
class SearchResult:
    """Normalised representation of a single web search result.

    Fields are provider-independent. Do not invent values for any field;
    leave them None if the provider did not supply them.
    """
    title: str
    url: str
    excerpts: list[str] = field(default_factory=list)
    source_domain: Optional[str] = None
    publish_date: Optional[str] = None          # ISO date string if available
    retrieval_timestamp: str = ""               # UTC ISO 8601
    provider: str = "unknown"
    relevance_score: Optional[float] = None
    citation_id: Optional[str] = None

    def __post_init__(self):
        if not self.retrieval_timestamp:
            self.retrieval_timestamp = datetime.now(timezone.utc).isoformat()
        if self.url and not self.source_domain:
            self.source_domain = _extract_domain(self.url)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "excerpts": self.excerpts,
            "source_domain": self.source_domain,
            "publish_date": self.publish_date,
            "retrieval_timestamp": self.retrieval_timestamp,
            "provider": self.provider,
            "relevance_score": self.relevance_score,
            "citation_id": self.citation_id,
        }


@dataclass
class SearchResponse:
    """The full response from a search operation."""
    results: list[SearchResult] = field(default_factory=list)
    query: str = ""
    provider: str = "unknown"
    search_id: Optional[str] = None
    total_results: int = 0
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.total_results = len(self.results)

    def to_dict(self) -> dict:
        return {
            "results": [r.to_dict() for r in self.results],
            "query": self.query,
            "provider": self.provider,
            "search_id": self.search_id,
            "total_results": self.total_results,
            "limitations": self.limitations,
        }


@dataclass
class ExtractResult:
    """Normalised content extracted from a single URL."""
    url: str
    title: Optional[str] = None
    excerpts: list[str] = field(default_factory=list)
    full_content: Optional[str] = None         # truncated to safe limit
    publish_date: Optional[str] = None
    retrieval_timestamp: str = ""
    provider: str = "unknown"
    extraction_objective: Optional[str] = None
    content_chars: int = 0
    error: Optional[str] = None

    def __post_init__(self):
        if not self.retrieval_timestamp:
            self.retrieval_timestamp = datetime.now(timezone.utc).isoformat()
        if self.full_content:
            self.content_chars = len(self.full_content)

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "excerpts": self.excerpts,
            "full_content": self.full_content,
            "publish_date": self.publish_date,
            "retrieval_timestamp": self.retrieval_timestamp,
            "provider": self.provider,
            "extraction_objective": self.extraction_objective,
            "content_chars": self.content_chars,
            "error": self.error,
        }


@dataclass
class ExtractResponse:
    """The full response from an extract operation."""
    results: list[ExtractResult] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)
    provider: str = "unknown"
    extract_id: Optional[str] = None
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "results": [r.to_dict() for r in self.results],
            "errors": self.errors,
            "provider": self.provider,
            "extract_id": self.extract_id,
            "limitations": self.limitations,
        }


@dataclass
class ResearchTaskRecord:
    """Metadata for a long-running deep-research task.

    Stored locally; compatible with a future Firestore document.
    """
    task_id: str                                # local UUID
    question: str
    status: str = "pending"                    # pending | running | completed | failed | cancelled
    provider: str = "unknown"
    provider_run_id: Optional[str] = None      # Parallel run_id or equivalent
    processor: str = "pro"                     # pro | ultra (Parallel tiers)
    created_at: str = ""
    updated_at: str = ""
    completed_at: Optional[str] = None
    owner_uid: Optional[str] = None            # reserved for Firebase Auth UID
    error_message: Optional[str] = None
    result: Optional[dict] = None              # populated when status == completed

    def __post_init__(self):
        now = datetime.now(timezone.utc).isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "question": self.question,
            "status": self.status,
            "provider": self.provider,
            "provider_run_id": self.provider_run_id,
            "processor": self.processor,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "owner_uid": self.owner_uid,
            "error_message": self.error_message,
            "result": self.result,
        }


@dataclass
class MonitorRecord:
    """Metadata for an ongoing web monitoring subscription."""
    monitor_id: str
    query: str
    status: str = "active"                     # active | paused | deleted | error
    provider: str = "unknown"
    provider_monitor_id: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    last_checked_at: Optional[str] = None
    last_event_at: Optional[str] = None
    owner_uid: Optional[str] = None
    error_message: Optional[str] = None
    findings: list[dict] = field(default_factory=list)  # recent events

    def __post_init__(self):
        now = datetime.now(timezone.utc).isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now

    def to_dict(self) -> dict:
        return {
            "monitor_id": self.monitor_id,
            "query": self.query,
            "status": self.status,
            "provider": self.provider,
            "provider_monitor_id": self.provider_monitor_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_checked_at": self.last_checked_at,
            "last_event_at": self.last_event_at,
            "owner_uid": self.owner_uid,
            "error_message": self.error_message,
            "findings": self.findings[-20:],   # cap at 20 most recent
        }


# ---------------------------------------------------------------------------
# Abstract provider interface
# ---------------------------------------------------------------------------

class ResearchProvider:
    """Abstract base for research provider implementations.

    All methods must be implementable without network access (for local fallback).
    Implementations must not raise unhandled exceptions — return error-bearing
    response objects instead.
    """

    def name(self) -> str:
        raise NotImplementedError

    def is_available(self) -> bool:
        """Return True if the provider can serve requests right now."""
        raise NotImplementedError

    def search(self, query: str, search_queries: list[str] | None = None,
               max_results: int = 10) -> SearchResponse:
        """Search for cybersecurity information matching the query."""
        raise NotImplementedError

    def extract(self, urls: list[str], objective: str | None = None) -> ExtractResponse:
        """Extract structured content from the given URLs."""
        raise NotImplementedError

    def create_research_task(self, question: str, processor: str = "pro",
                             task_input=None, task_spec: dict | None = None) -> ResearchTaskRecord:
        """Create a long-running research task; returns immediately with task metadata."""
        raise NotImplementedError

    def get_task_result(self, task_record: ResearchTaskRecord) -> ResearchTaskRecord:
        """Poll the provider for task status and, if complete, populate result."""
        raise NotImplementedError

    def create_monitor(self, query: str, owner_uid: str | None = None) -> MonitorRecord:
        """Create an ongoing monitor for new information matching the query."""
        raise NotImplementedError

    def list_monitors(self, owner_uid: str | None = None) -> list[MonitorRecord]:
        """List monitors owned by the specified user (or all if uid is None)."""
        raise NotImplementedError

    def get_monitor_events(self, monitor: MonitorRecord) -> dict:
        """Read recent events for one configured monitor."""
        raise NotImplementedError

    def delete_monitor(self, monitor_id: str) -> bool:
        """Delete or deactivate a monitor. Return True on success."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_domain(url: str) -> str:
    """Extract the registered domain from a URL string."""
    m = re.search(r"https?://([^/?\s]+)", url or "")
    if not m:
        return ""
    host = m.group(1).lstrip("www.").split(":")[0]
    return host
