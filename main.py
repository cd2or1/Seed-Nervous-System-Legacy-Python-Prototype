"""Application entry: mount the native extension through :class:`StreamBroker`."""

from __future__ import annotations

import sys

from core.stream_broker import StreamBroker


def main() -> int:
    broker = StreamBroker()
    broker.inject_core()
    _ = broker.check_health()
    if not broker.is_attached:
        print(
            "Warning: running with stub or degraded kernel. See [Stream Routing] lines above.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
