"""Individual check implementations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CheckResult:
    """Uniform result shape for every kind of check."""

    up: bool
    latency_ms: float | None = None
    packet_loss: float | None = None
    status_code: int | None = None
    ssl_days_left: int | None = None
    detail: str | None = None


__all__ = ["CheckResult"]
