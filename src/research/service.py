"""Research subsystem service layer.

Sits between the HTTP server routes and the provider/store implementations.
Handles:
- Provider selection (Parallel vs. local fallback based on PARALLEL_API_KEY)
- Input validation (length, type, content)
- SSRF guard for URL extraction
- Prompt injection defence for local model summarisation
- Normalised error responses
- Per-user task and monitor ownership enforcement

All public functions return plain dicts suitable for JSON serialisation.
No exceptions propagate beyond this module; errors are returned as
{"error": "..."} dicts and callers check the "error" key.
"""
from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import Optional

from src.research import task_store
from src.research.ssrf_guard import SSRFError, validate_extract_urls

# ---------------------------------------------------------------------------
# Provider selection
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _get_provider():
    """Select and cache the best available provider.

    Returns a ParallelProvider if PARALLEL_API_KEY is set; otherwise returns
    a LocalFallbackProvider. The provider is cached after the first call; to
    reload after setting the key, restart the server.
    """
    from src.research.config import get_parallel_api_key
    api_key = get_parallel_api_key()
    if api_key:
        try:
            from src.research.parallel_client import ParallelProvider
            return ParallelProvider()
        except Exception:
            pass
    from src.research.local_fallback import LocalFallbackProvider
    return LocalFallbackProvider()


def get_provider_status() -> dict:
    """Return provider connectivity status without exposing secrets."""
    from src.research.config import get_parallel_api_key
    api_key = get_parallel_api_key()
    has_key = bool(api_key)
    provider = _get_provider()
    return {
        "provider": provider.name(),
        "api_key_configured": has_key,
        "is_available": provider.is_available(),
        "mode": "live-web" if has_key else "local-only",
        "note": (
            "Live web research is active." if has_key
            else "No PARALLEL_API_KEY configured. Using local corpus only."
        ),
    }


# ---------------------------------------------------------------------------
# Input helpers
# ---------------------------------------------------------------------------

MAX_QUERY_LEN = 2000
MAX_QUESTION_LEN = 8000
MAX_OBJECTIVE_LEN = 2000

_INJECTION_PATTERN = re.compile(
    r"\b(ignore|disregard|override|forget)\b.{0,80}"
    r"\b(instructions?|system prompt|previous|above|rules?)\b",
    re.I,
)


def _validate_query(query: str, name: str = "query", max_len: int = MAX_QUERY_LEN) -> str:
    query = (query or "").strip()
    if not query:
        raise ValueError(f"{name} is required")
    if len(query) > max_len:
        raise ValueError(f"{name} exceeds the {max_len} character limit")
    return query


def _check_injection(text: str) -> bool:
    """Return True if the text appears to contain a prompt injection attempt."""
    return bool(_INJECTION_PATTERN.search(text))


# ---------------------------------------------------------------------------
# Feature A: Web Search
# ---------------------------------------------------------------------------

def search(query: str, search_queries: Optional[list] = None,
           max_results: int = 10) -> dict:
    """Search public sources for cybersecurity information.

    Args:
        query: Natural-language research objective.
        search_queries: Optional 2–3 specific keyword queries.
        max_results: Maximum results to return (capped at 30).

    Returns dict with keys: results, query, provider, search_id, limitations.
    """
    try:
        query = _validate_query(query, "query")
    except ValueError as exc:
        return {"error": str(exc)}

    if search_queries is not None:
        if not isinstance(search_queries, list):
            return {"error": "search_queries must be a list of strings"}
        if len(search_queries) > 3:
            return {"error": "At most 3 search_queries may be provided"}
        search_queries = [
            str(q)[:100] for q in search_queries
            if isinstance(q, str) and q.strip()
        ][:3]
        if any(not 3 <= len(q.split()) <= 6 for q in search_queries):
            return {"error": "Each keyword search query must contain 3 to 6 words"}

    max_results = min(max(1, int(max_results or 10)), 30)

    provider = _get_provider()
    try:
        response = provider.search(query, search_queries=search_queries, max_results=max_results)
    except Exception:
        return {"error": "Research provider encountered an error. Try again later."}

    return response.to_dict()


def quick_answer(question: str, effort: str = "low") -> dict:
    """Ask Parallel Responses for an opt-in, cited answer based on live research."""
    try:
        question = _validate_query(question, "question", MAX_QUESTION_LEN)
    except ValueError as exc:
        return {"error": str(exc)}
    if effort not in {"low", "medium", "high"}:
        return {"error": "effort must be low, medium, or high"}
    provider = _get_provider()
    if provider.name() != "parallel" or not hasattr(provider, "quick_answer"):
        return {"error": "Configure PARALLEL_API_KEY to use live researched answers."}
    try:
        return provider.quick_answer(question, effort=effort)
    except Exception:
        return {"error": "Parallel Responses request failed. Check provider status and try again."}


def _findall_provider():
    provider = _get_provider()
    if provider.name() != "parallel" or not hasattr(provider, "findall_ingest"):
        return None
    return provider


def findall_ingest(objective: str) -> dict:
    try:
        objective = _validate_query(objective, "objective", MAX_QUESTION_LEN)
    except ValueError as exc:
        return {"error": str(exc)}
    if _check_injection(objective):
        return {"error": "Research objective appears to contain embedded instructions. Please rephrase."}
    provider = _findall_provider()
    if provider is None:
        return {"error": "Configure PARALLEL_API_KEY to use FindAll entity discovery."}
    try:
        return provider.findall_ingest(objective)
    except Exception:
        return {"error": "FindAll could not prepare the discovery schema. Try again later."}


def findall_create(objective: str, entity_type: str, match_conditions: list,
                   generator: str = "preview", match_limit: int = 5) -> dict:
    try:
        objective = _validate_query(objective, "objective", MAX_QUESTION_LEN)
    except ValueError as exc:
        return {"error": str(exc)}
    if not isinstance(entity_type, str) or not entity_type.strip() or len(entity_type) > 120:
        return {"error": "entity_type must be a non-empty string of at most 120 characters"}
    if not isinstance(match_conditions, list) or not 1 <= len(match_conditions) <= 12:
        return {"error": "match_conditions must contain between 1 and 12 conditions"}
    clean_conditions = []
    for index, condition in enumerate(match_conditions):
        if not isinstance(condition, dict) or set(condition) - {"name", "description"}:
            return {"error": f"match_conditions[{index}] must contain only name and description"}
        name, description = condition.get("name"), condition.get("description")
        if not isinstance(name, str) or not name.strip() or len(name) > 100:
            return {"error": f"match_conditions[{index}].name must be a string of at most 100 characters"}
        if not isinstance(description, str) or not description.strip() or len(description) > 1000:
            return {"error": f"match_conditions[{index}].description must be a string of at most 1000 characters"}
        clean_conditions.append({"name": name.strip(), "description": description.strip()})
    if generator not in {"preview", "base", "core", "pro"}:
        return {"error": "generator must be preview, base, core, or pro"}
    try:
        match_limit = int(match_limit)
    except (TypeError, ValueError):
        return {"error": "match_limit must be an integer"}
    if generator == "preview" and not 5 <= match_limit <= 10:
        return {"error": "preview match_limit must be between 5 and 10"}
    if generator != "preview" and not 1 <= match_limit <= 25:
        return {"error": "match_limit must be between 1 and 25"}
    if _check_injection(objective):
        return {"error": "Research objective appears to contain embedded instructions. Please rephrase."}
    provider = _findall_provider()
    if provider is None:
        return {"error": "Configure PARALLEL_API_KEY to use FindAll entity discovery."}
    schema = {"objective": objective, "entity_type": entity_type.strip(),
              "match_conditions": clean_conditions, "generator": generator,
              "match_limit": match_limit}
    try:
        return provider.findall_create(schema)
    except Exception:
        return {"error": "FindAll could not start the discovery run. Check account status and try again."}


def findall_status(findall_id: str, include_result: bool = False) -> dict:
    if not isinstance(findall_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", findall_id):
        return {"error": "Invalid FindAll run ID"}
    provider = _findall_provider()
    if provider is None:
        return {"error": "Configure PARALLEL_API_KEY to view FindAll results."}
    try:
        return provider.findall_status(findall_id, include_result=include_result)
    except Exception:
        return {"error": "FindAll run status is unavailable. Try again later."}


# ---------------------------------------------------------------------------
# Feature B: Content Extraction
# ---------------------------------------------------------------------------

def extract(urls: list, objective: Optional[str] = None) -> dict:
    """Extract structured content from public URLs.

    Validates all URLs for SSRF safety before sending to the provider.
    Extracted content is treated as untrusted.

    Args:
        urls: List of HTTPS URLs to extract (up to 20).
        objective: Optional extraction focus description.

    Returns dict with keys: results, errors, provider, extract_id, limitations.
    """
    if not isinstance(urls, list):
        return {"error": "urls must be a list of strings"}
    if not urls:
        return {"error": "At least one URL is required"}

    try:
        valid_urls, validation_errors = validate_extract_urls(urls)
    except ValueError as exc:
        return {"error": str(exc)}

    if objective is not None:
        if not isinstance(objective, str):
            return {"error": "objective must be a string"}
        objective = objective[:MAX_OBJECTIVE_LEN]

    provider = _get_provider()

    if not valid_urls:
        # All URLs rejected — still return a proper response with errors
        from src.research.provider import ExtractResponse
        return ExtractResponse(
            results=[],
            errors=validation_errors,
            provider=provider.name(),
            limitations=["All submitted URLs were rejected by the safety validator."],
        ).to_dict()

    try:
        response = provider.extract(valid_urls, objective=objective)
    except Exception:
        return {"error": "Research provider encountered an error during extraction."}

    # Merge any pre-validation errors into the provider response
    response.errors.extend(validation_errors)
    return response.to_dict()


# ---------------------------------------------------------------------------
# Feature C: Deep Research Tasks
# ---------------------------------------------------------------------------

def create_research_task(question: str, processor: str = "pro",
                         owner_uid: Optional[str] = None) -> dict:
    """Start a long-running research task.

    For the Parallel 'pro' processor, the task runs for up to ~10 minutes.
    The task is persisted locally; poll get_task_status with the returned
    task_id to retrieve the result.

    Args:
        question: The research question (up to 8000 chars).
        processor: Parallel processor tier ('pro' or 'ultra').
        owner_uid: Optional user UID for ownership enforcement.

    Returns dict with task_id, status, and metadata.
    """
    try:
        question = _validate_query(question, "question", MAX_QUESTION_LEN)
    except ValueError as exc:
        return {"error": str(exc)}

    # Reject obvious prompt injection in the research question
    if _check_injection(question):
        return {"error": "Research question appears to contain embedded instructions. Please rephrase."}

    valid_processors = {"pro", "ultra", "base", "core", "lite"}
    processor = processor if processor in valid_processors else "pro"

    provider = _get_provider()
    try:
        record = provider.create_research_task(question, processor=processor)
        # Attach owner if provided
        if owner_uid:
            record.owner_uid = owner_uid
            task_store.update_task(record)
    except Exception:
        return {"error": "Failed to create research task. Try again later."}

    return record.to_dict()


_ENRICHMENT_FIELDS = {
    "affected_products": "Affected products and version ranges explicitly named by reputable sources.",
    "cve_ids": "CVE identifiers explicitly associated with this security record.",
    "severity": "Published severity and scoring system, if available.",
    "exploitation_status": "Evidence of exploitation, distinguishing confirmed exploitation from speculation.",
    "mitigations": "Vendor-published mitigations or fixed versions; state when unavailable.",
    "vendor_advisory_url": "Canonical vendor advisory URL supporting this record.",
}


def create_enrichment_task(record: dict, fields: list[str], processor: str = "base") -> dict:
    """Enrich a public security record with schema-validated, cited fields."""
    if not isinstance(record, dict) or not record:
        return {"error": "record must be a non-empty object"}
    allowed_input = {"id", "title", "vendor", "product", "version", "description", "source_url"}
    if set(record) - allowed_input:
        return {"error": "record may include only id, title, vendor, product, version, description, and source_url"}
    normalized = {}
    for key, value in record.items():
        if not isinstance(value, str) or len(value) > 2000:
            return {"error": f"record.{key} must be a string of at most 2000 characters"}
        normalized[key] = value.strip()
    if not any(normalized.values()):
        return {"error": "record must include at least one non-empty value"}
    if len(str(normalized).encode("utf-8")) > 8000:
        return {"error": "record exceeds the 8000 byte limit"}
    if "source_url" in normalized:
        try:
            normalized["source_url"] = validate_extract_urls([normalized["source_url"]])[0][0]
        except (ValueError, IndexError):
            return {"error": "source_url must be a public HTTPS URL"}
    if not isinstance(fields, list) or not 1 <= len(fields) <= len(_ENRICHMENT_FIELDS):
        return {"error": "Select between one and six enrichment fields"}
    if any(not isinstance(field, str) or field not in _ENRICHMENT_FIELDS for field in fields):
        return {"error": "One or more enrichment fields are unsupported"}
    fields = list(dict.fromkeys(fields))
    provider = _get_provider()
    if provider.name() != "parallel":
        return {"error": "Structured web enrichment requires the configured Parallel provider; no external request was made."}
    properties = {field: {"type": "string", "description": _ENRICHMENT_FIELDS[field]} for field in fields}
    task_spec = {"output_schema": {"type": "json", "json_schema": {
        "type": "object", "properties": properties, "required": fields,
        "additionalProperties": False,
    }}}
    question = "Enrich the public cybersecurity record using current, reputable web sources. Return only supported values and cite evidence per field."
    try:
        task = provider.create_research_task(
            question, processor=processor, task_input={"security_record": normalized}, task_spec=task_spec,
        )
        return task.to_dict()
    except Exception:
        return {"error": "Failed to create enrichment task. Try again later."}


def get_task_status(task_id: str, poll: bool = True,
                    owner_uid: Optional[str] = None) -> dict:
    """Get the current status and result of a research task.

    Args:
        task_id: The task ID returned by create_research_task.
        poll: If True and the task is still running, polls the provider.
        owner_uid: If provided, enforces ownership check.

    Returns dict with task metadata and result when completed.
    """
    if not task_id or not isinstance(task_id, str):
        return {"error": "task_id is required"}

    record = task_store.get_task(task_id)
    if record is None:
        return {"error": "Task not found"}

    # Ownership check
    if owner_uid is not None and record.owner_uid != owner_uid:
        return {"error": "Task not found"}  # Don't reveal existence

    # If task is still running and polling is requested
    if poll and record.status in ("running", "pending") and record.provider_run_id:
        provider = _get_provider()
        try:
            record = provider.get_task_result(record)
        except Exception:
            pass  # Return last known state

    return record.to_dict()


def list_research_tasks(owner_uid: Optional[str] = None) -> dict:
    """List research tasks, optionally filtered by owner."""
    tasks = task_store.list_tasks(owner_uid=owner_uid, limit=50)
    return {
        "tasks": [
            {k: t.to_dict()[k] for k in
             ("task_id", "question", "status", "provider", "processor",
              "created_at", "updated_at", "completed_at", "error_message")}
            for t in tasks
        ],
        "total": len(tasks),
    }


# ---------------------------------------------------------------------------
# Feature D: Monitors
# ---------------------------------------------------------------------------

def create_monitor(query: str, owner_uid: Optional[str] = None) -> dict:
    """Create an ongoing monitor for new cybersecurity information.

    Args:
        query: The monitoring objective (up to 2000 chars).
        owner_uid: Optional user UID for ownership.

    Returns dict with monitor metadata.
    """
    try:
        query = _validate_query(query, "query")
    except ValueError as exc:
        return {"error": str(exc)}

    provider = _get_provider()
    try:
        record = provider.create_monitor(query, owner_uid=owner_uid)
    except Exception:
        return {"error": "Failed to create monitor. Try again later."}

    return record.to_dict()


def list_monitors(owner_uid: Optional[str] = None) -> dict:
    """List monitors owned by the user."""
    provider = _get_provider()
    monitors = provider.list_monitors(owner_uid=owner_uid)
    return {
        "monitors": [m.to_dict() for m in monitors],
        "total": len(monitors),
        "note": (
            "Monitors in local mode do not perform live web polling. "
            "Configure PARALLEL_API_KEY for live monitoring."
            if provider.name() == "local"
            else "Monitors are active."
        ),
    }


def get_monitor_events(monitor_id: str, owner_uid: Optional[str] = None) -> dict:
    if not isinstance(monitor_id, str) or not re.fullmatch(r"monitor_[a-f0-9]{32}", monitor_id):
        return {"error": "Monitor not found"}
    monitor = task_store.get_monitor(monitor_id)
    if monitor is None or (owner_uid is not None and monitor.owner_uid != owner_uid):
        return {"error": "Monitor not found"}
    provider = _get_provider()
    try:
        return provider.get_monitor_events(monitor)
    except Exception:
        return {"error": "Could not retrieve monitor events. Try again later."}


def delete_monitor_by_id(monitor_id: str, owner_uid: Optional[str] = None) -> dict:
    """Delete a monitor by ID.

    Args:
        monitor_id: The monitor ID.
        owner_uid: If provided, enforces ownership check.

    Returns {"deleted": True} on success or {"error": "..."} on failure.
    """
    if not monitor_id or not isinstance(monitor_id, str):
        return {"error": "monitor_id is required"}

    record = task_store.get_monitor(monitor_id)
    if record is None:
        return {"error": "Monitor not found"}

    if owner_uid is not None and record.owner_uid != owner_uid:
        return {"error": "Monitor not found"}

    provider = _get_provider()
    try:
        ok = provider.delete_monitor(monitor_id)
    except Exception:
        return {"error": "Failed to delete monitor"}

    return {"deleted": ok, "monitor_id": monitor_id}
