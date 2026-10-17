"""Secure environment configuration loader for the research subsystem.

Loads PARALLEL_API_KEY from os.environ or a local .env file.
Standard library only; zero external dependencies.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT / ".env"

_ENV_LOADED = False


def load_env(env_path: Path | None = None) -> None:
    """Load configuration from .env into os.environ if not already present.

    - Reads key=value pairs, ignoring comments and blank lines.
    - Strips matching quotes.
    - Does NOT overwrite existing os.environ entries.
    - Silently handles missing files or permission errors.
    """
    global _ENV_LOADED
    if _ENV_LOADED and env_path is None:
        return
    path = env_path or ENV_FILE
    if not path.is_file():
        _ENV_LOADED = True
        return
    try:
        content = path.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip()
                if len(val) >= 2 and (
                    (val.startswith('"') and val.endswith('"'))
                    or (val.startswith("'") and val.endswith("'"))
                ):
                    val = val[1:-1]
                if key and key not in os.environ:
                    os.environ[key] = val
    except OSError:
        pass
    _ENV_LOADED = True


def get_parallel_api_key() -> str:
    """Return the sanitized PARALLEL_API_KEY from environment or .env."""
    key = os.environ.get("PARALLEL_API_KEY", "").strip()
    if not key and not _ENV_LOADED:
        load_env()
        key = os.environ.get("PARALLEL_API_KEY", "").strip()
    return key
