"""Host OS system telemetry collection module."""

from __future__ import annotations

import asyncio
import logging
import shutil
import time
from typing import Any, Dict, List, Optional

import psutil

logger = logging.getLogger(__name__)

# Cache previous network counters for speed calculations
_prev_net_io: Any = None
_prev_time: Optional[float] = None


async def get_gpu_stats() -> Dict[str, Any]:
    """Retrieve GPU information using nvidia-smi command-line query."""
    # Find nvidia-smi path
    smi_path = shutil.which("nvidia-smi")
    if not smi_path:
        return {
            "available": False,
            "name": None,
            "usagePct": None,
            "memoryTotalGb": None,
            "memoryUsedGb": None,
        }

    try:
        # Query: GPU Name, GPU Utilization %, Memory Total (MiB), Memory Used (MiB)
        cmd = [
            smi_path,
            "--query-gpu=name,utilization.gpu,memory.total,memory.used",
            "--format=csv,noheader,nounits",
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=1.5)

        if proc.returncode == 0:
            output = stdout.decode("utf-8").strip()
            if output:
                parts = output.split(",")
                if len(parts) >= 4:
                    return {
                        "available": True,
                        "name": parts[0].strip(),
                        "usagePct": float(parts[1].strip()),
                        "memoryTotalGb": round(float(parts[2].strip()) / 1024.0, 2),
                        "memoryUsedGb": round(float(parts[3].strip()) / 1024.0, 2),
                    }
    except Exception as exc:
        logger.debug("Failed to query nvidia-smi: %s", exc)

    return {
        "available": False,
        "name": None,
        "usagePct": None,
        "memoryTotalGb": None,
        "memoryUsedGb": None,
    }


def get_network_speed() -> Dict[str, float]:
    """Calculate average network upload and download speed (bytes/sec) since last call."""
    global _prev_net_io, _prev_time

    try:
        net_io = psutil.net_io_counters()
        curr_time = time.time()

        upload_speed = 0.0
        download_speed = 0.0

        if _prev_net_io is not None and _prev_time is not None:
            time_delta = curr_time - _prev_time
            if time_delta > 0:
                bytes_sent_delta = net_io.bytes_sent - _prev_net_io.bytes_sent
                bytes_recv_delta = net_io.bytes_recv - _prev_net_io.bytes_recv
                # Ensure no negative wrap-arounds (e.g. interfaces rebooted)
                upload_speed = max(0.0, bytes_sent_delta / time_delta)
                download_speed = max(0.0, bytes_recv_delta / time_delta)

        _prev_net_io = net_io
        _prev_time = curr_time

        return {
            "uploadSpeedBytesSec": round(upload_speed, 2),
            "downloadSpeedBytesSec": round(download_speed, 2),
        }
    except Exception as exc:
        logger.debug("Failed to fetch net_io_counters: %s", exc)
        return {
            "uploadSpeedBytesSec": 0.0,
            "downloadSpeedBytesSec": 0.0,
        }


def get_storage_volumes() -> List[Dict[str, Any]]:
    """Enumerate disk volumes/partitions and space usage details."""
    volumes = []
    try:
        partitions = psutil.disk_partitions(all=False)
        for part in partitions:
            # Skip loop devices, CD-ROMs or empty mounts on Windows/Linux
            if not part.mountpoint or "cdrom" in part.opts or "loop" in part.device:
                continue

            # Skip read-only mounts that might cause block on reading usage
            if "ro" in part.opts:
                continue

            try:
                usage = psutil.disk_usage(part.mountpoint)
                volumes.append(
                    {
                        "mount": part.mountpoint,
                        "totalGb": round(usage.total / (1024**3), 2),
                        "usedGb": round(usage.used / (1024**3), 2),
                        "pct": round(usage.percent, 1),
                    }
                )
            except (PermissionError, FileNotFoundError):
                # Drives like floppy/uninitialized USB partitions can raise PermissionError
                continue
            except Exception:
                continue
    except Exception as exc:
        logger.warning("Failed to retrieve disk partitions: %s", exc)

    return volumes


async def get_host_stats() -> Dict[str, Any]:
    """Retrieve full Host OS telemetry stats snapshot."""
    # CPU
    try:
        # Non-blocking query of CPU usage percentage since last call
        cpu_usage = psutil.cpu_percent(interval=None)
        cpu_cores = psutil.cpu_count(logical=True) or 1
    except Exception:
        cpu_usage = 0.0
        cpu_cores = 1

    # RAM
    try:
        ram = psutil.virtual_memory()
        ram_total = round(ram.total / (1024**3), 2)
        ram_used = round(ram.used / (1024**3), 2)
        ram_pct = round(ram.percent, 1)
    except Exception:
        ram_total = 0.0
        ram_used = 0.0
        ram_pct = 0.0

    # GPU
    gpu = await get_gpu_stats()

    # Network Speed
    network = get_network_speed()

    # Storage Volumes
    storage = get_storage_volumes()

    return {
        "cpu": {
            "usagePct": cpu_usage,
            "cores": cpu_cores,
        },
        "ram": {
            "totalGb": ram_total,
            "usedGb": ram_used,
            "pct": ram_pct,
        },
        "gpu": gpu if gpu["available"] else None,
        "storage": storage,
        "network": network,
    }
