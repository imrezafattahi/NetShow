"""Processor, memory, disk and network usage of the machine running NetShow."""

from __future__ import annotations

import os
import time

import psutil

GB = 1024 ** 3
_ROOT = os.path.abspath(os.sep)
_previous: dict[str, float] = {}


def sample() -> dict[str, float]:
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(_ROOT)
    net = psutil.net_io_counters()
    now = time.monotonic()

    recv_kbps = sent_kbps = 0.0
    if _previous:
        window = max(now - _previous["ts"], 0.001)
        recv_kbps = max(net.bytes_recv - _previous["recv"], 0) / window / 1024
        sent_kbps = max(net.bytes_sent - _previous["sent"], 0) / window / 1024
    _previous.update(ts=now, recv=net.bytes_recv, sent=net.bytes_sent)

    return {
        "cpu": round(psutil.cpu_percent(interval=None), 1),
        "ram": round(memory.percent, 1),
        "ram_total_gb": round(memory.total / GB, 1),
        "disk": round(disk.percent, 1),
        "disk_total_gb": round(disk.total / GB, 1),
        "net_recv_kbps": round(recv_kbps, 1),
        "net_sent_kbps": round(sent_kbps, 1),
    }
