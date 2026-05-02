"""License anchor: file-based binding; no machine-ID hard-coding (fingerprint = SHA256 of key only)."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .runtime_paths import get_core_home

_ANCHOR_NAME = "core_environment_anchor.json"
_LEGACY_ANCHOR_NAME = "anima_environment_anchor.json"


def _anchor_path_for_read() -> Path:
    h = get_core_home()
    primary = h / _ANCHOR_NAME
    if primary.is_file():
        return primary
    legacy = h / _LEGACY_ANCHOR_NAME
    if legacy.is_file():
        return legacy
    return primary


def _anchor_path_for_write() -> Path:
    return get_core_home() / _ANCHOR_NAME


def _path_report() -> dict[str, str]:
    h = (os.environ.get("CORE_HOME") or "").strip()
    if not h:
        h = (os.environ.get("ANIMA_HOME") or "").strip()
    if h:
        return {"data_root": "CORE_HOME", "anchor_name": _ANCHOR_NAME}
    return {"data_root": "CWD (CORE_HOME unset)", "anchor_name": _ANCHOR_NAME}


def check_anchor_health() -> dict[str, Any]:
    p = _anchor_path_for_read()
    meta = _path_report()
    if not p.is_file():
        return {
            "status": "missing",
            **meta,
        }
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"status": "corrupt", **meta}
    except (OSError, json.JSONDecodeError) as e:
        return {
            "status": "corrupt",
            "error": type(e).__name__,
            **meta,
        }
    return {
        "status": "ok",
        **meta,
    }


def rebind_environment_anchor(license_key: str) -> dict[str, Any]:
    p = _anchor_path_for_write()
    key = str(license_key or "").strip()
    if not key:
        return {"status": "error", "message": "empty license key"}
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        h = hashlib.sha256(key.encode("utf-8")).hexdigest()
        payload: dict[str, object] = {"fingerprint": h, "key_present": 1}
        p.write_text(json.dumps(payload, indent=0) + "\n", encoding="utf-8")
        return {
            "status": "rebound",
            "message": "License anchor written. Restart the kernel to apply.",
        }
    except OSError as e:
        return {"status": "error", "message": str(e)}
