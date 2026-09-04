"""TLS certificate expiry check."""

from __future__ import annotations

import asyncio
import socket
import ssl
from datetime import datetime, timezone


def _days_left(host: str, port: int, timeout: float) -> tuple[int | None, str | None]:
    context = ssl.create_default_context()
    try:
        with socket.create_connection((host, port), timeout=timeout) as raw:
            with context.wrap_socket(raw, server_hostname=host) as tls:
                cert = tls.getpeercert()
    except (OSError, ssl.SSLError) as exc:
        return None, f"TLS handshake failed: {exc}"[:200]

    not_after = (cert or {}).get("notAfter")
    if not not_after:
        return None, "certificate has no expiry field"
    expires = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
    return (expires - datetime.now(timezone.utc)).days, None


async def check_tls(host: str, port: int = 443, timeout: float = 6.0) -> tuple[int | None, str | None]:
    """Return (days until expiry, error message). Both may be None."""
    return await asyncio.to_thread(_days_left, host, port, timeout)
