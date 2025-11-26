from __future__ import annotations

import os
import platform
import re
import subprocess
import sys
import time
from typing import Optional

from langchain.tools import tool

from ..observability.metrics import monitor_tool

def _total_memory_bytes() -> Optional[int]:
    """Best-effort total system memory."""
    try:
        page_size = os.sysconf("SC_PAGE_SIZE")
        phys_pages = os.sysconf("SC_PHYS_PAGES")
        return int(page_size) * int(phys_pages)
    except (AttributeError, ValueError, OSError):
        pass

    if sys.platform == "win32":  # pragma: win32-no-cover
        try:
            import ctypes

            k32 = ctypes.windll.kernel32
            mem_kb = ctypes.c_ulonglong()
            if k32.GetPhysicallyInstalledSystemMemory(ctypes.byref(mem_kb)):
                return int(mem_kb.value) * 1024
        except Exception:
            return None

    return None


def _uptime_seconds() -> Optional[int]:
    """Return uptime in seconds (best effort)."""
    if os.name == "posix":
        try:
            with open("/proc/uptime", "r", encoding="utf8") as handle:
                return int(float(handle.readline().split()[0]))
        except (OSError, ValueError):
            pass

        if sys.platform == "darwin":
            try:
                output = subprocess.check_output(
                    ["sysctl", "-n", "kern.boottime"],
                    text=True,
                ).strip()
                match = re.search(r"sec\s*=\s*(\d+)", output)
                if match:
                    boot_ts = int(match.group(1))
                    return int(time.time() - boot_ts)
            except (subprocess.SubprocessError, ValueError, OSError):
                return None
    elif sys.platform == "win32":  # pragma: win32-no-cover
        try:
            import ctypes

            GetTickCount64 = ctypes.windll.kernel32.GetTickCount64
            GetTickCount64.restype = ctypes.c_ulonglong
            return int(GetTickCount64() // 1000)
        except Exception:
            return None

    return None


@tool("os_info")
@monitor_tool
def os_info() -> dict:
    """Get host OS information (platform, architecture, CPUs, memory, uptime)."""
    return {
        "error": False,
        "platform": platform.system(),
        "release": platform.release(),
        "arch": platform.machine(),
        "cpus": os.cpu_count(),
        "memory": _total_memory_bytes(),
        "uptime_seconds": _uptime_seconds(),
    }


__all__ = ["os_info"]
