"""Lightweight JSONL artifact logging."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import get_settings


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_jsonl(log_name: str, payload: dict[str, Any]) -> Path:
    settings = get_settings()
    out = settings.logs_dir / f"{log_name}.jsonl"
    entry = {"timestamp": utc_now_iso(), **payload}
    with out.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return out
