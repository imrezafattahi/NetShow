"""ICMP check built on the system `ping` binary, so no root privileges needed."""

from __future__ import annotations

import asyncio
import platform
import re

from . import CheckResult

_LOSS = re.compile(r"(\d+(?:\.\d+)?)\s*%\s*(?:packet\s+)?loss", re.I)
_AVG_UNIX = re.compile(r"min/avg/max[^=]*=\s*[\d.]+/([\d.]+)/", re.I)
_AVG_WIN = re.compile(r"(?:Average|\u0645\u062a\u0648\u0633\u0637)\s*=\s*(\d+)\s*ms", re.I)
_TIMES = re.compile(r"time\s*[=<]\s*(\d+(?:\.\d+)?)\s*ms", re.I)


def parse_ping(output: str) -> CheckResult:
    """Pull latency and packet loss out of ping output (Linux, macOS, Windows)."""
    loss_match = _LOSS.search(output)
    packet_loss = float(loss_match.group(1)) if loss_match else None

    latency: float | None = None
    for pattern in (_AVG_UNIX, _AVG_WIN):
        match = pattern.search(output)
        if match:
            latency = float(match.group(1))
            break
    if latency is None:
        samples = [float(v) for v in _TIMES.findall(output)]
        if samples:
            latency = round(sum(samples) / len(samples), 2)

    reachable = latency is not None and (packet_loss is None or packet_loss < 100)
    detail = None if reachable else (output.strip().splitlines() or ["no response"])[-1][:200]
    return CheckResult(
        up=reachable,
        latency_ms=latency,
        packet_loss=packet_loss if packet_loss is not None else (None if reachable else 100.0),
        detail=detail,
    )


def _command(host: str, count: int, timeout: int) -> list[str]:
    if platform.system().lower().startswith("win"):
        return ["ping", "-n", str(count), "-w", str(timeout * 1000), host]
    return ["ping", "-c", str(count), "-W", str(timeout), host]


async def check_ping(host: str, count: int = 3, timeout: int = 2) -> CheckResult:
    try:
        proc = await asyncio.create_subprocess_exec(
            *_command(host, count, timeout),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        raw, _ = await asyncio.wait_for(proc.communicate(), timeout=count * timeout + 6)
    except FileNotFoundError:
        return CheckResult(up=False, detail="ping command not available on this host")
    except asyncio.TimeoutError:
        return CheckResult(up=False, packet_loss=100.0, detail="ping timed out")
    except OSError as exc:  # pragma: no cover - platform dependent
        return CheckResult(up=False, detail=f"ping failed: {exc}")

    return parse_ping(raw.decode("utf-8", errors="ignore"))
