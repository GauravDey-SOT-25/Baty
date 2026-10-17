"""Local fallback research provider.

Used when no external API key is configured. Implements all ResearchProvider
methods using the existing local infrastructure:
- Search: delegates to src.incident_search.search_incidents (lexical BM25)
- Extract: not supported (returns a clear limitation message)
- Research tasks: runs synchronously using local LLM + incident search
- Monitors: stored locally with no live web polling

This provider never makes outbound network requests.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from src.research.provider import (
    ExtractResponse,
    ExtractResult,
    MonitorRecord,
    ResearchProvider,
    ResearchTaskRecord,
    SearchResponse,
    SearchResult,
)
from src.research import task_store


_PROVIDER_NAME = "local"
_SEARCH_LIMITATIONS = [
    "Local search is lexical keyword matching over a dated local corpus (CISA KEV, CISA advisories, Hacker News sample).",
    "No live web search is performed. Results reflect the local snapshot at indexing time.",
    "Configure PARALLEL_API_KEY for live web search.",
]
_EXTRACT_LIMITATIONS = [
    "Web content extraction requires a configured research provider (PARALLEL_API_KEY).",
    "In local-only mode, extraction is not available.",
]


class LocalFallbackProvider(ResearchProvider):
    """Research provider using only local resources."""

    def name(self) -> str:
        return _PROVIDER_NAME

    def is_available(self) -> bool:
        return True  # always available

    def search(self, query: str, search_queries: list[str] | None = None,
               max_results: int = 10) -> SearchResponse:
        """Search local incident/advisory corpus."""
        from src.incident_search.search import search_incidents

        # Combine query and any provided keyword queries
        combined = query
        if search_queries:
            combined += " " + " ".join(search_queries)

        raw = search_incidents(combined.strip(), limit=min(max_results, 10))
        incidents = raw.get("incidents", [])

        results = []
        for item in incidents:
            source_url = item.get("source_url") or ""
            title = item.get("title") or item.get("id") or "Untitled"
            summary = item.get("summary") or item.get("text") or ""
            excerpts = [summary[:800]] if summary else []
            result = SearchResult(
                title=title,
                url=source_url,
                excerpts=excerpts,
                publish_date=item.get("published_at"),
                provider=_PROVIDER_NAME,
                citation_id=item.get("id"),
            )
            results.append(result)

        return SearchResponse(
            results=results,
            query=query,
            provider=_PROVIDER_NAME,
            search_id="local_" + uuid.uuid4().hex[:12],
            limitations=_SEARCH_LIMITATIONS + raw.get("limitations", []),
        )

    def extract(self, urls: list[str], objective: str | None = None) -> ExtractResponse:
        """Not available in local mode."""
        errors = [{"url": u, "error": "extraction not available in local-only mode"} for u in urls]
        return ExtractResponse(
            results=[],
            errors=errors,
            provider=_PROVIDER_NAME,
            limitations=_EXTRACT_LIMITATIONS,
        )

    def create_research_task(self, question: str, processor: str = "pro") -> ResearchTaskRecord:
        """Run a synchronous local research using incident search + local model."""
        record = task_store.create_task(
            question=question,
            provider=_PROVIDER_NAME,
            processor="local",
        )
        # Run synchronously (local inference is fast enough for a direct response)
        record.status = "running"
        task_store.update_task(record)
        try:
            result = self._run_local_research(question)
            record.status = "completed"
            record.result = result
            record.completed_at = datetime.now(timezone.utc).isoformat()
        except Exception as exc:
            record.status = "failed"
            record.error_message = f"Local research failed: {type(exc).__name__}"
        task_store.update_task(record)
        return record

    def get_task_result(self, task_record: ResearchTaskRecord) -> ResearchTaskRecord:
        """Return the stored task (local tasks complete synchronously on create)."""
        stored = task_store.get_task(task_record.task_id)
        return stored if stored is not None else task_record

    def create_monitor(self, query: str, owner_uid: str | None = None) -> MonitorRecord:
        """Create a locally-stored monitor (no live web polling in local mode)."""
        record = task_store.create_monitor(
            query=query,
            provider=_PROVIDER_NAME,
            owner_uid=owner_uid,
        )
        return record

    def list_monitors(self, owner_uid: str | None = None) -> list[MonitorRecord]:
        return task_store.list_monitors(owner_uid=owner_uid)

    def get_monitor_events(self, monitor: MonitorRecord) -> dict:
        return {
            "events": monitor.findings[-20:],
            "provider": _PROVIDER_NAME,
            "note": "Local monitors do not poll the public web; no new events were fetched.",
        }

    def delete_monitor(self, monitor_id: str) -> bool:
        return task_store.delete_monitor(monitor_id)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _run_local_research(self, question: str) -> dict:
        """Produce a local research result using incident search + local model."""
        from src.incident_search.search import search_incidents
        from src.assistant.local_model import answer_locally

        search_raw = search_incidents(question, limit=5)
        incidents = search_raw.get("incidents", [])
        sources = [
            {
                "title": item.get("title") or item.get("id") or "",
                "text": item.get("text") or item.get("summary") or "",
                "url": item.get("source_url") or "",
                "published_at": item.get("published_at") or "",
            }
            for item in incidents
        ]

        model_answer = answer_locally(question, sources=sources, max_tokens=512)
        if model_answer is None:
            model_answer = (
                "The local language model is unavailable. "
                "Matched local records are shown in the sources below."
            )

        citations = [
            {
                "id": item.get("id"),
                "title": item.get("title") or item.get("id"),
                "url": item.get("source_url"),
                "published_at": item.get("published_at"),
            }
            for item in incidents
            if item.get("source_url")
        ]

        return {
            "summary": model_answer,
            "key_findings": [],
            "sources": citations,
            "limitations": [
                "This is a local research result using lexical search over a dated corpus.",
                "The local model may produce inaccurate or incomplete answers.",
                "No live web search was performed.",
                "Configure PARALLEL_API_KEY for live deep research.",
            ],
            "provider": _PROVIDER_NAME,
            "corpus_records_searched": search_raw.get("corpus_records", 0),
        }
