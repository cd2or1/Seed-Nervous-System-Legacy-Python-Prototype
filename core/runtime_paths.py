"""Path helpers for the Core runtime (portable, no hard-coded host paths)."""

from __future__ import annotations

import os
from pathlib import Path


def get_core_home() -> Path:
    """Resolve data home: ``CORE_HOME`` first, then legacy ``ANIMA_HOME``, else current working directory."""
    v = (os.environ.get("CORE_HOME") or os.environ.get("ANIMA_HOME") or "").strip()
    if v:
        return Path(v).expanduser().resolve()
    return Path.cwd().resolve()


def get_anima_home() -> Path:
    """Deprecated alias for :func:`get_core_home` (migration only)."""
    return get_core_home()


def get_package_core_dir() -> Path:
    """Directory of this ``core`` *package* (sibling to ``stream_broker``); portable on all platforms."""
    return Path(__file__).resolve().parent


def get_core_search_bases() -> list[Path]:
    """Order: ``$CORE_HOME/core`` (user data) first, then bundled package ``core/``; deduplicated after ``resolve``."""
    seen: set[Path] = set()
    out: list[Path] = []
    for base in (get_core_home() / "core", get_package_core_dir()):
        r = base.resolve()
        if r in seen:
            continue
        seen.add(r)
        out.append(r)
    return out
