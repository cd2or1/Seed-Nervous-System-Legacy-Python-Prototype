#!/usr/bin/env python3
"""
Safe terminology refactor: replace biological product names with engineering terms.

Mappings (applied in order; longer phrases first):
  "Nervous System"           -> "Logic Routing"
  "Neural Core"              -> "Kernel"
  "neural core"              -> "kernel"
  "VascularBroker"           -> "StreamBroker"
  "vascular_broker"          -> "stream_broker"
  "Vascular System"          -> "Stream"
  "Vascular"                 -> "Stream"
  "vascular"                 -> "stream"
  "ThalamusCore"             -> "LogicCore"
  "Thalamus"                 -> "KernelHandle"  # class discovery only; verify extension exports
  "thalamus" (module paths)  -> keep in ABI comments only — script skips binary globs by default

Environment / files (optional --migrate-env):
  ANIMA_HOME -> CORE_HOME (in .py, .md, .json text; not in refactor_names.py itself when dry-run lists)

Usage:
  python refactor_names.py --dry-run
  python refactor_names.py --apply
  python refactor_names.py --apply --also-rename-legacy-settings  # copies anima_settings*.json if present

This repository is already migrated; the script is for forks or older trees.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# (old, new) — order matters: longer keys first where needed
TEXT_REPLACEMENTS: list[tuple[str, str]] = [
    ("Nervous System", "Logic Routing"),
    ("Neural Core", "Kernel"),
    ("neural core", "kernel"),
    ("VascularBroker", "StreamBroker"),
    ("vascular_broker", "stream_broker"),
    ("Vascular System", "Stream"),
    ("[Vascular System]", "[Stream]"),
    ("Vascular", "Stream"),
    ("vascular", "stream"),
    ("ThalamusCore", "LogicCore"),
    # Do not replace ANIMA_* env keys in code here: current tree keeps legacy fallbacks.
    # Migrate JSON keys manually or use --also-rename-legacy-settings on old anima_settings files only.
    ("anima_settings", "core_settings"),
    ("anima_probe_", "core_probe_"),
    ("Anima ", "Core "),
    ("Anima:", "Core:"),
    ("Anima/", "Core/"),
]

SKIP_NAMES = {
    "refactor_names.py",
    ".git",
    "__pycache__",
    ".pyc",
    ".zip",
    ".pyd",
    ".so",
    ".dylib",
    ".dll",
    ".gguf",
}


# Native loader may still need legacy export symbol names from the binary ABI.
SKIP_REFACTOR_PATHS = {
    ROOT / "core" / "stream_broker.py",
}


def _should_skip_path(p: Path) -> bool:
    rel = p.relative_to(ROOT).as_posix()
    parts = rel.split("/")
    if any(x in parts for x in (".git", "__pycache__", ".idea", ".vscode")):
        return True
    if p.resolve() in SKIP_REFACTOR_PATHS:
        return True
    suf = p.suffix.lower()
    if suf in (".pyd", ".so", ".dll", ".dylib", ".zip", ".gguf", ".png", ".jpg"):
        return True
    if p.name in SKIP_NAMES:
        return True
    return False


def _transform(text: str) -> tuple[str, int]:
    n = 0
    out = text
    for old, new in TEXT_REPLACEMENTS:
        c = out.count(old)
        if c:
            out = out.replace(old, new)
            n += c
    return out, n


def iter_text_files() -> list[Path]:
    files: list[Path] = []
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        if _should_skip_path(p):
            continue
        if p.suffix.lower() in (
            ".py",
            ".md",
            ".json",
            ".txt",
            ".toml",
            ".yml",
            ".yaml",
            ".ini",
            ".cfg",
        ):
            files.append(p)
    return sorted(files)


def cmd_dry_run() -> int:
    total = 0
    for p in iter_text_files():
        raw = p.read_text(encoding="utf-8")
        new, n = _transform(raw)
        if n:
            print(f"{p.relative_to(ROOT)}: {n} replacement(s)")
            total += n
    print(f"--- total replacements if applied: {total}")
    return 0


def cmd_apply() -> int:
    for p in iter_text_files():
        raw = p.read_text(encoding="utf-8")
        new, n = _transform(raw)
        if n and new != raw:
            p.write_text(new, encoding="utf-8", newline="\n")
            print(f"updated {p.relative_to(ROOT)} ({n})")
    return 0


def cmd_migrate_legacy_settings() -> int:
    for name in (
        "anima_settings.json.example",
        "anima_settings.low.json",
        "anima_settings.normal.json",
        "anima_settings.turbo.json",
    ):
        src = ROOT / name
        if not src.is_file():
            continue
        dst = ROOT / name.replace("anima_settings", "core_settings")
        shutil.copy2(src, dst)
        raw = dst.read_text(encoding="utf-8")
        new, _ = _transform(raw)
        dst.write_text(new, encoding="utf-8", newline="\n")
        print(f"migrated {src.name} -> {dst.name}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Biological → engineering terminology refactor")
    ap.add_argument("--dry-run", action="store_true", help="list files that would change")
    ap.add_argument("--apply", action="store_true", help="write transformed text files")
    ap.add_argument(
        "--also-rename-legacy-settings",
        action="store_true",
        help="copy anima_settings*.json to core_settings*.json with key renames",
    )
    args = ap.parse_args()
    if not args.dry_run and not args.apply and not args.also_rename_legacy_settings:
        ap.print_help()
        return 1
    r = 0
    if args.dry_run:
        r = cmd_dry_run()
    if args.apply:
        r = cmd_apply()
    if args.also_rename_legacy_settings:
        r = cmd_migrate_legacy_settings()
    return r


if __name__ == "__main__":
    sys.exit(main())
