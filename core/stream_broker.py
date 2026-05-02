"""Stream broker: load native kernel extension with stub fallback (no biological naming in user-visible paths)."""

from __future__ import annotations

import importlib.util
import os
import re
import sys
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from types import ModuleType
from typing import Any

from .runtime_paths import get_core_search_bases, get_package_core_dir

# Prefer engineering-prefixed artifacts; legacy biological filenames still discovered for shipped wheels.
_EXTENSION_GLOBS = (
    "kernel*.pyd",
    "kernel*.so",
    "kernel*.dylib",
    "thalamus*.pyd",
    "thalamus*.so",
    "thalamus*.dylib",
)

# CPython import name must match PyInit_* in the built extension (ABI contract with existing binaries).
_EXTENSION_MODULE_ABI_NAME = "thalamus"


def _stream_print(msg: str) -> None:
    print(f"[Stream Routing] {msg}", flush=True)


def _pyd_stem() -> str:
    return f"cp{sys.version_info.major}{sys.version_info.minor}"


def _extract_cp_tag(pyd_name: str) -> str | None:
    m = re.search(r"\.(cp\d+)-", pyd_name, re.IGNORECASE)
    return m.group(1).lower() if m else None


def _is_cp_tag_compatible(artifact_path: Path) -> bool:
    """If the filename encodes a CPython ABI, require a match; otherwise allow (unversioned name)."""
    n = artifact_path.name
    wtag = _extract_cp_tag(n)
    if wtag is not None:
        return wtag == _pyd_stem().lower()
    m = re.search(r"cpython-(\d+)\.(\d+)", n, re.IGNORECASE)
    if m:
        return (int(m.group(1)), int(m.group(2))) == (sys.version_info.major, sys.version_info.minor)
    m2 = re.search(r"cpython-3(\d{1,2})[._-]", n, re.IGNORECASE)
    if m2 and sys.version_info.major == 3:
        return int(m2.group(1)) == sys.version_info.minor
    if re.search(r"cpython|cp[0-9]+", n, re.IGNORECASE) is None:
        return True
    return False


def _iter_native_artifacts() -> list[Path]:
    found: list[Path] = []
    for base in get_core_search_bases():
        if not base.is_dir():
            continue
        for g in _EXTENSION_GLOBS:
            for p in sorted(base.glob(g)):
                if p.is_file():
                    found.append(p)
    return found


def _default_native_path() -> Path:
    """Resolve extension: ``$CORE_HOME/core`` first, then package ``core/``; then compatible tag, else first file."""
    stem = _pyd_stem()
    for base in get_core_search_bases():
        if not base.is_dir():
            continue
        if os.name == "nt":
            for prefix in ("kernel", "thalamus"):
                w = base / f"{prefix}.{stem}-win_amd64.pyd"
                if w.is_file() and _is_cp_tag_compatible(w):
                    return w
        for prefix in ("kernel", "thalamus"):
            for p in sorted(base.glob(f"{prefix}.cpython-*.so")) + sorted(
                base.glob(f"{prefix}.cpython-*.dylib"),
            ):
                if p.is_file() and _is_cp_tag_compatible(p):
                    return p
        for prefix in ("kernel", "thalamus"):
            for d in (base / f"{prefix}.{stem}.pyd", base / f"{prefix}.{stem}.so"):
                if d.is_file() and _is_cp_tag_compatible(d):
                    return d
    for p in _iter_native_artifacts():
        if _is_cp_tag_compatible(p):
            return p
    for p in _iter_native_artifacts():
        return p
    if os.name == "nt":
        return get_package_core_dir() / f"kernel.{stem}-win_amd64.pyd"
    return get_package_core_dir() / f"kernel.cpython-{sys.version_info.major}.{sys.version_info.minor}.so"


def _public_artifact_label(filename: str) -> str:
    """User-facing label: map legacy ``thalamus*`` filenames to ``kernel*`` for display only."""
    lower = filename.lower()
    if lower.startswith("thalamus"):
        return "kernel" + filename[8:]
    return filename


def _redacted_load_error(kind: str, name: str, extra: str = "") -> str:
    label = _public_artifact_label(name)
    if extra and not any(c in extra for c in (":", "\\", "/")):
        return f"{kind}: {label} — {extra}"
    return f"{kind}: {label}"


def _redacted_exception(e: BaseException) -> str:
    return f"{type(e).__name__}"


class BaseLogicCore(ABC):
    """Abstract logic surface for the host application."""

    @abstractmethod
    def process_impulse(self, *args: Any, **kwargs: Any) -> Any: ...

    @abstractmethod
    def check_health(self) -> Any: ...


class StubCore(BaseLogicCore):
    """Offline stand-in when the native extension is missing or incompatible."""

    def process_impulse(self, *args: Any, **kwargs: Any) -> str:
        return "Core Offline"

    def check_health(self) -> dict[str, Any]:
        return {"status": "offline", "message": "Core Offline", "impl": "stub"}


class PydModuleCore(BaseLogicCore):
    """Wraps a loaded native module (ABI name fixed by extension build)."""

    def __init__(self, mod: ModuleType) -> None:
        self._mod = mod

    def process_impulse(self, *args: Any, **kwargs: Any) -> Any:
        for name in ("process_text", "process_impulse"):
            fn = getattr(self._mod, name, None)
            if callable(fn):
                return fn(*args, **kwargs)
        # Legacy symbol names sometimes exported by older extension builds
        for attr in ("KernelHandle", "Core", "LogicCore", "Thalamus", "ThalamusCore"):
            item = getattr(self._mod, attr, None)
            if item is None:
                continue
            o: Any = item
            if isinstance(item, type):
                try:
                    o = item()  # type: ignore[misc]
                except (TypeError, OSError):
                    _stream_print(
                        f"factory skip: extension class {attr!r} not constructible.",
                    )
                    continue
            for name in ("process_text", "process_impulse"):
                fn = getattr(o, name, None)
                if callable(fn):
                    return fn(*args, **kwargs)
        raise RuntimeError("native extension has no process_text/process_impulse")

    def check_health(self) -> Any:
        fn = getattr(self._mod, "check_health", None)
        if callable(fn):
            return fn()
        return {
            "status": "ok",
            "source": "pyd",
            "module": getattr(self._mod, "__name__", EXTENSION_MODULE_ABI_NAME),
        }


def _load_native_module(artifact_path: Path) -> ModuleType:
    name = EXTENSION_MODULE_ABI_NAME
    spec = importlib.util.spec_from_file_location(name, str(artifact_path), submodule_search_locations=[])
    if spec is None or spec.loader is None:
        raise ImportError("spec_from_file_location failed for native extension")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


class StreamBroker:
    """Attaches the native kernel extension; ``inject_core`` searches ``$CORE_HOME/core`` before package ``core/``."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._pyd_path: Path | None = None
        self._core: BaseLogicCore = StubCore()
        self._load_error: str | None = None
        self._load_ok: bool = False

    @property
    def core_dir(self) -> Path:
        return get_package_core_dir()

    @staticmethod
    def _default_pyd_path(explicit: Path | None) -> Path:
        if explicit is not None:
            return Path(explicit).expanduser()
        return _default_native_path()

    def inject_core(self, path: str | Path | None = None) -> None:
        with self._lock:
            self._pyd_path = self._default_pyd_path(Path(path) if path is not None else None)
            self._rebind_core()

    def _ensure_injected(self) -> None:
        with self._lock:
            if self._pyd_path is None:
                self._pyd_path = self._default_pyd_path(None)
                self._rebind_core()

    def _rebind_core(self) -> None:
        assert self._pyd_path is not None
        self._load_error = None
        self._load_ok = False
        n = self._pyd_path.name
        if not self._pyd_path.is_file():
            self._load_error = _redacted_load_error("binary not found", n)
            _stream_print(f"Kernel load failed: missing artifact — {_public_artifact_label(n)} (stub).")
            self._core = StubCore()
            return
        if not _is_cp_tag_compatible(self._pyd_path):
            self._load_error = _redacted_load_error("ABI tag mismatch", n, sys.version.split()[0])
            _stream_print(
                f"Kernel refused: need ABI {_pyd_stem()!r} for this interpreter "
                f"({sys.version_info.major}.{sys.version_info.minor}); file tag differs.",
            )
            _stream_print("Telemetry: Kernel — compatibility gate (MISMATCH).")
            self._core = StubCore()
            return
        cdir = str(self._pyd_path.parent.resolve())
        if cdir not in sys.path:
            sys.path.insert(0, cdir)
            _stream_print("sys.path primed: extension parent (OK) — no absolute path logged.")
        try:
            mod = _load_native_module(self._pyd_path.resolve())
            self._core = PydModuleCore(mod)
            self._load_ok = True
            _stream_print("Kernel Attached: Stable")
            _stream_print("Telemetry: Logic Kernel — LOAD OK.")
        except Exception as e:
            self._load_error = f"{_redacted_exception(e)}"
            _stream_print(
                f"Kernel load failed: {_redacted_exception(e)} — stub. (no user paths.)",
            )
            self._core = StubCore()

    def process_impulse(self, *args: Any, **kwargs: Any) -> Any:
        with self._lock:
            self._ensure_injected()
            return self._core.process_impulse(*args, **kwargs)

    def check_health(self) -> Any:
        with self._lock:
            self._ensure_injected()
            return self._core.check_health()

    @property
    def is_attached(self) -> bool:
        with self._lock:
            self._ensure_injected()
            return self._load_ok and not isinstance(self._core, StubCore)

    @property
    def last_error(self) -> str | None:
        with self._lock:
            return self._load_error
