"""HTTP and HTTPS availability check."""

from __future__ import annotations

import time

import httpx

from . import CheckResult

USER_AGENT = "NetShow/0.1 (+https://github.com/imrezafattahi/NetShow)"


async def check_http(url: str, timeout: float = 10.0, ok_below: int = 400) -> CheckResult:
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            response = await client.get(url, headers={"User-Agent": USER_AGENT})
    except httpx.TimeoutException:
        return CheckResult(up=False, detail=f"no response within {timeout:.0f}s")
    except httpx.HTTPError as exc:
        return CheckResult(up=False, detail=f"{type(exc).__name__}: {exc}"[:200])

    elapsed = round((time.perf_counter() - started) * 1000, 1)
    healthy = response.status_code < ok_below
    return CheckResult(
        up=healthy,
        latency_ms=elapsed,
        status_code=response.status_code,
        detail=None if healthy else f"HTTP {response.status_code} {response.reason_phrase}",
    )
