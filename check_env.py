"""Environment checker for cross-platform Core runtime delivery."""

from __future__ import annotations

import ctypes.util
import os
import platform
import shutil
import socket
import tempfile
from pathlib import Path

from core.runtime_paths import get_core_home
from core.security import check_anchor_health
from core.stream_broker import StreamBroker


def _os_label() -> str:
    return f"{platform.system()} {platform.release()} ({platform.machine()})"


def _has_llama_server() -> bool:
    return shutil.which("llama-server") is not None or shutil.which("llama-server.exe") is not None


def _has_metal_runtime() -> bool:
    if platform.system().lower() != "darwin":
        return False
    return ctypes.util.find_library("Metal") is not None


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        try:
            return s.connect_ex(("127.0.0.1", port)) == 0
        except OSError:
            return False


def _port_owner_hint(port: int) -> str:
    try:
        import psutil  # type: ignore

        for c in psutil.net_connections(kind="tcp"):
            if c.laddr and int(c.laddr.port) == port and c.status == psutil.CONN_LISTEN:
                pid = int(c.pid or 0)
                if pid <= 0:
                    return "unknown process"
                try:
                    p = psutil.Process(pid)
                    return f"{p.name()} (pid={pid})"
                except Exception:
                    return f"pid={pid}"
    except Exception:
        return "unknown process"
    return "unknown process"


def _cuda_available() -> bool | None:
    try:
        import torch  # type: ignore

        return bool(torch.cuda.is_available())
    except Exception:
        return None


def _path_writable(path: Path) -> tuple[bool, str]:
    try:
        path.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(prefix="core_probe_", suffix=".test", dir=str(path), delete=True) as _:
            pass
        return True, "ok"
    except Exception as exc:
        return False, str(exc)


def _recommended_mode() -> str:
    sys_name = platform.system().lower()
    machine = platform.machine().lower()
    if sys_name == "darwin" and machine in ("arm64", "aarch64"):
        return "Normal" if _has_metal_runtime() else "Low"
    if sys_name == "windows":
        return "Normal"
    return "Low"


def _env_port(name: str, legacy: str, default: int) -> str:
    return str(os.environ.get(name) or os.environ.get(legacy) or default)


def main() -> None:
    print("=== Core Environment Check ===")
    print(f"OS: {_os_label()}")
    print(f"Python: {platform.python_version()}")
    ch = os.environ.get("CORE_HOME") or os.environ.get("ANIMA_HOME")
    print(f"CORE_HOME: {(ch or '(unset)')}")
    home = get_core_home()
    print(f"Resolved Home: {home}")
    print(f"llama-server on PATH: {'YES' if _has_llama_server() else 'NO'}")

    anchor = check_anchor_health()
    anchor_status = str(anchor.get("status") or "unknown").upper()
    print(f"Anchor: {anchor_status}")
    if str(anchor.get("status") or "") in ("changed", "corrupt"):
        print("Advice: Anchor mismatch or corruption detected. Re-enter your license key or contact support.")
    elif str(anchor.get("status") or "") == "missing":
        print("Advice: First run requires anchor activation. Start the kernel and enter your License Key.")

    busy_8082 = _port_in_use(8082)
    busy_8083 = _port_in_use(8083)
    print(f"Port 8082: {'BUSY' if busy_8082 else 'FREE'}")
    print(f"Port 8083: {'BUSY' if busy_8083 else 'FREE'}")
    chat_port = _env_port("CORE_CHAT_PORT", "ANIMA_CHAT_PORT", 8082)
    logic_port = _env_port("CORE_LOGIC_PORT", "ANIMA_LOGIC_PORT", 8083)
    if busy_8082:
        print(
            f"Advice: 8082 is occupied by {_port_owner_hint(8082)}. "
            f"Please close that process or change CORE_CHAT_PORT (legacy: ANIMA_CHAT_PORT). Current: {chat_port}."
        )
    if busy_8083:
        print(
            f"Advice: 8083 is occupied by {_port_owner_hint(8083)}. "
            f"Please close that process or change CORE_LOGIC_PORT (legacy: ANIMA_LOGIC_PORT). Current: {logic_port}."
        )

    sys_name = platform.system().lower()
    if sys_name == "darwin":
        metal_ok = _has_metal_runtime()
        print(f"Metal runtime: {'YES' if metal_ok else 'NO'}")
        if not metal_ok:
            print("Advice: your environment is Mac without Metal runtime; use Low performance mode.")

    cuda = _cuda_available()
    if cuda is None:
        print("CUDA runtime: torch not installed (skip)")
    else:
        print(f"CUDA runtime: {'YES' if cuda else 'NO'}")
        if not cuda and platform.system().lower() == "windows":
            print("Advice: NVIDIA runtime unavailable. Install CUDA runtime or switch to Low mode (CPU).")

    writable, reason = _path_writable(home)
    print(f"Home writable: {'YES' if writable else 'NO'}")
    if not writable:
        print(
            "Advice: CORE_HOME is not writable. "
            "Avoid system root paths and choose a user directory (e.g. a dedicated data folder on a data drive)."
        )
        print(f"Detail: {reason}")

    mode = _recommended_mode()
    print(f"Recommended CORE_PERF_MODE: {mode}")
    settings = Path.cwd() / "core_settings.json"
    print(f"Tip: set \"CORE_PERF_MODE\": \"{mode}\" in {settings.name}")

    print("--- Stream Routing / Logic Kernel ---")
    b = StreamBroker()
    b.inject_core()
    h = b.check_health()
    if b.is_attached:
        print("Logic Kernel: attached (StreamBroker mount OK, runtime permission implied).")
    else:
        print("Logic Kernel: offline / stub (binary missing, incompatible, or load error).")
    if b.last_error:
        print(f"  Stream Routing last_error: {b.last_error}")
    print(f"  Stream Routing check_health: {h}")


if __name__ == "__main__":
    main()
