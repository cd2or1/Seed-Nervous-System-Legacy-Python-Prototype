"""
Latency harness for :class:`StreamBroker` (Seed kernel package).

- 10 × ~512 token text pulses
- :func:`time.perf_counter_ns` around ``process_impulse``
- Mean Overhead = mean(total − underlying) per trial
- Logic Jitter = sample stdev of total latency (ms)
"""

from __future__ import annotations

import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.stream_broker import StreamBroker  # noqa: E402

TRIALS = 10
_APPROX_BYTES_PER_TOKEN = 4.0
_TARGET_TOKENS = 512


def _build_512_token_pulse() -> str:
    need = int(_TARGET_TOKENS * _APPROX_BYTES_PER_TOKEN)
    unit = (
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 4
    )
    return (unit * (need // len(unit) + 1))[:need]


def _ns_to_ms(ns: int) -> float:
    return ns / 1_000_000.0


def _find_infer_ms(result: Any) -> float | None:
    if isinstance(result, dict):
        for k in (
            "inference_ms",
            "infer_ms",
            "llm_ms",
            "model_ms",
            "backend_ms",
            "infer_time_ms",
        ):
            v = result.get(k)
            if isinstance(v, (int, float)) and v >= 0:
                return float(v)
    return None


def _baseline_from_env() -> float:
    raw = (os.environ.get("SEED_INFER_BASELINE_MS") or "").strip()
    if not raw:
        return 0.0
    return float(raw)


def main() -> int:
    pulse = _build_512_token_pulse()
    broker = StreamBroker()
    broker.inject_core()
    if not broker.is_attached:
        print(
            "[latency_test] Warning: Logic Kernel not attached (stub or load error). "
            "Overhead is dominated by broker/stub; set SEED_INFER_BASELINE_MS to compare.",
            file=sys.stderr,
        )

    static_baseline = _baseline_from_env()
    total_ms_list: list[float] = []
    overhead_ms_list: list[float] = []
    last_result: Any = None

    for i in range(TRIALS):
        t0 = time.perf_counter_ns()
        last_result = broker.process_impulse(pulse)
        t1 = time.perf_counter_ns()
        total_ms = _ns_to_ms(t1 - t0)
        total_ms_list.append(total_ms)

        inferred = _find_infer_ms(last_result)
        u_ms = inferred if inferred is not None else static_baseline

        overhead_ms_list.append(max(0.0, total_ms - u_ms))
        print(
            f"  trial {i + 1:2d}/{TRIALS}  total={total_ms:.4f} ms  "
            f"underlying~={u_ms:.4f} ms  overhead={overhead_ms_list[-1]:.4f} ms"
        )

    mean_total = statistics.fmean(total_ms_list)
    mean_overhead = statistics.fmean(overhead_ms_list)
    if len(total_ms_list) > 1:
        logic_jitter_ms = statistics.stdev(total_ms_list)
    else:
        logic_jitter_ms = 0.0

    print("---")
    print(f"Pulse length (approx, chars): {len(pulse)}  (~{_TARGET_TOKENS} tokens @ ~{_APPROX_BYTES_PER_TOKEN} char/token)")
    print(f"Mean total response time:     {mean_total:.4f} ms")
    print(f"Mean Overhead (ms):           {mean_overhead:.4f}  (= total - underlying, per trial)")
    print(
        f"  (underlying from return dict, else SEED_INFER_BASELINE_MS={static_baseline})"
    )
    print(f"Logic Jitter (ms, stdev of total over {TRIALS} runs): {logic_jitter_ms:.4f}")
    if _find_infer_ms(last_result) is None and static_baseline == 0.0:
        print(
            "Note: No inference timing was parsed from the return value and SEED_INFER_BASELINE_MS is unset; "
            "underlying inference time is treated as 0, so Overhead equals full call-chain latency."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
