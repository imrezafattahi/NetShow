"""Settings loading. Reads config.json, secrets come from the environment."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

DEFAULT_TARGETS: list[dict[str, str]] = [
    {"name": "Cloudflare DNS", "kind": "ping", "host": "1.1.1.1"},
    {"name": "Example site", "kind": "http", "url": "https://example.com"},
]


@dataclass(frozen=True)
class Target:
    """One thing we watch. `address` is a hostname/IP for ping, a URL for http."""

    name: str
    kind: str
    address: str

    @property
    def is_http(self) -> bool:
        return self.kind == "http"

    @property
    def hostname(self) -> str:
        """Bare hostname, useful for the TLS check."""
        addr = self.address
        if "://" in addr:
            addr = addr.split("://", 1)[1]
        addr = addr.split("/", 1)[0]
        if "@" in addr:
            addr = addr.split("@", 1)[1]
        if addr.startswith("[") and "]" in addr:  # IPv6 literal
            return addr[1 : addr.index("]")]
        return addr.split(":", 1)[0]

    @property
    def port(self) -> int:
        addr = self.address.split("://", 1)[-1].split("/", 1)[0]
        if addr.startswith("[") and "]:" in addr:
            return int(addr.split("]:", 1)[1])
        if addr.count(":") == 1:
            tail = addr.split(":", 1)[1]
            if tail.isdigit():
                return int(tail)
        return 443


@dataclass
class Settings:
    interval_seconds: int = 60
    history_days: int = 7
    fail_threshold: int = 2
    ssl_warn_days: int = 14
    targets: list[Target] = field(default_factory=list)
    db_path: Path = ROOT / "data" / "netshow.db"
    telegram_token: str | None = None
    telegram_chat_id: str | None = None

    @property
    def telegram_enabled(self) -> bool:
        return bool(self.telegram_token and self.telegram_chat_id)


def _parse_target(raw: dict[str, Any]) -> Target | None:
    kind = str(raw.get("kind") or raw.get("type") or "ping").lower()
    address = raw.get("url") if kind == "http" else raw.get("host")
    address = address or raw.get("host") or raw.get("url")
    name = raw.get("name") or address
    if not address or kind not in {"ping", "http"}:
        return None
    return Target(name=str(name), kind=kind, address=str(address))


def load_settings(path: str | Path | None = None) -> Settings:
    """Load settings from JSON. Missing or broken file falls back to defaults."""
    config_path = Path(path or os.getenv("NETSHOW_CONFIG") or ROOT / "config.json")
    raw: dict[str, Any] = {}
    if config_path.is_file():
        try:
            raw = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            raw = {}

    alerts = raw.get("alerts") or {}
    targets = [t for t in (_parse_target(r) for r in raw.get("targets") or DEFAULT_TARGETS) if t]

    db_env = os.getenv("NETSHOW_DB")
    return Settings(
        interval_seconds=max(int(raw.get("interval_seconds", 60)), 10),
        history_days=max(int(raw.get("history_days", 7)), 1),
        fail_threshold=max(int(alerts.get("fail_threshold", 2)), 1),
        ssl_warn_days=max(int(alerts.get("ssl_warn_days", 14)), 1),
        targets=targets,
        db_path=Path(db_env) if db_env else ROOT / "data" / "netshow.db",
        telegram_token=os.getenv("NETSHOW_TELEGRAM_TOKEN") or None,
        telegram_chat_id=os.getenv("NETSHOW_TELEGRAM_CHAT_ID") or None,
    )
