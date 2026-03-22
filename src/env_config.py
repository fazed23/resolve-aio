"""Project-local environment loading for ResolveAIO."""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILES = [
    PROJECT_ROOT / "config" / "resolve_aio.env",
    PROJECT_ROOT / ".env",
]


def _parse_env_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None

    key, value = stripped.split("=", 1)
    key = key.strip()
    value = value.strip().strip('"').strip("'")
    if not key:
        return None
    return key, value


def load_project_env() -> dict[str, str]:
    """Load known project env files into ``os.environ`` without overriding explicit env vars."""
    loaded: dict[str, str] = {}

    for env_file in ENV_FILES:
        if not env_file.exists():
            continue
        for raw_line in env_file.read_text().splitlines():
            parsed = _parse_env_line(raw_line)
            if not parsed:
                continue
            key, value = parsed
            if key not in os.environ and value:
                os.environ[key] = value
                loaded[key] = value

    return loaded
