"""Stability: ``CORE_HOME`` + :class:`StreamBroker` search order (no personal paths in output)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(_ROOT))

from core.runtime_paths import get_core_search_bases, get_package_core_dir
from core.stream_broker import StreamBroker


def main() -> int:
    pkg = get_package_core_dir()
    tdir = Path(tempfile.mkdtemp(prefix="core_h_"))
    h1 = tdir / "a"
    h2 = tdir / "b"
    h1.mkdir()
    h2.mkdir()
    (h1 / "core").mkdir()
    (h2 / "core").mkdir()
    (h2 / "core" / "marker").write_text("x", encoding="utf-8")

    old_core = os.environ.get("CORE_HOME")
    old_anima = os.environ.get("ANIMA_HOME")
    try:
        os.environ["CORE_HOME"] = str(h1)
        if "ANIMA_HOME" in os.environ:
            del os.environ["ANIMA_HOME"]
        b1 = get_core_search_bases()
        if b1[0] != h1 / "core":
            print("FAIL: first base should be CORE_HOME/core", file=__import__("sys").stderr)
            return 1
        if pkg not in b1:
            print("FAIL: package core/ must appear in search bases", file=__import__("sys").stderr)
            return 1
        v = StreamBroker()
        v.inject_core()
        h = v.check_health()
        print("OK: CORE_HOME=temp → broker check_health() returned:", h)
        os.environ["CORE_HOME"] = str(h2)
        b2 = get_core_search_bases()
        if b2[0] != h2 / "core":
            return 1
        print("OK: re-pointed CORE_HOME, first base updates:", b2[0] == h2 / "core")
    finally:
        if old_core is None:
            os.environ.pop("CORE_HOME", None)
        else:
            os.environ["CORE_HOME"] = old_core
        if old_anima is None:
            os.environ.pop("ANIMA_HOME", None)
        else:
            os.environ["ANIMA_HOME"] = old_anima

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
