"""One-click license repair tool for environment rebind."""

from __future__ import annotations

import os
import sys

from core.security import check_anchor_health, rebind_environment_anchor


def main() -> int:
    print("=== Core License Repair ===")
    state = check_anchor_health()
    print(f"Current anchor status: {state.get('status', 'unknown')}")
    if str(state.get("status") or "") in ("ok", "corrupt"):
        print(
            f"Anchor location: {state.get('data_root', 'unknown')}"
            f" / {state.get('anchor_name', 'core_environment_anchor.json')}"
        )

    key = str(
        os.environ.get("CORE_LICENSE_KEY") or os.environ.get("ANIMA_LICENSE_KEY") or "",
    ).strip()
    if not key:
        try:
            key = input("Enter your Gumroad License Key: ").strip()
        except Exception:
            key = ""
    if not key:
        print("License Key is empty. Rebind cancelled.")
        return 1

    result = rebind_environment_anchor(key)
    print(str(result.get("message") or "Operation completed."))
    if str(result.get("status") or "") != "rebound":
        return 2

    verify = check_anchor_health()
    print(f"Verify status: {verify.get('status', 'unknown')}")
    if str(verify.get("status") or "") != "ok":
        print("Post-rebind verification failed. Please contact support.")
        return 3
    print("License restore successful. You can restart the kernel now.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
