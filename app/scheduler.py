"""The check loop: run every target, store results, raise alerts, prune history."""

from __future__ import annotations

import asyncio
import logging

from .alerts import Alerter
from .checks import CheckResult
from .checks.host import sample as host_sample
from .checks.ping import check_ping
from .checks.tls import check_tls
from .checks.web import check_http
from .config import Settings, Target
from .db import Database

log = logging.getLogger("netshow.scheduler")


class Monitor:
    def __init__(self, settings: Settings, db: Database) -> None:
        self.settings = settings
        self.db = db
        self.alerter = Alerter(settings)
        self.failures: dict[str, int] = {}
        self.notified_down: set[str] = set()
        self.notified_ssl: set[str] = set()
        self.cycles = 0

    async def check(self, target: Target) -> CheckResult:
        if target.is_http:
            result = await check_http(target.address)
            if target.address.lower().startswith("https://"):
                days, error = await check_tls(target.hostname, target.port)
                result.ssl_days_left = days
                if error and result.detail is None:
                    result.detail = error
            return result
        return await check_ping(target.address)

    async def _handle_alerts(self, target: Target, result: CheckResult) -> None:
        name = target.name
        if result.up:
            self.failures[name] = 0
            if name in self.notified_down:
                self.notified_down.discard(name)
                self.db.add_event(name, "up")
                await self.alerter.up(name)
        else:
            self.failures[name] = self.failures.get(name, 0) + 1
            if self.failures[name] >= self.settings.fail_threshold and name not in self.notified_down:
                self.notified_down.add(name)
                self.db.add_event(name, "down", result.detail)
                await self.alerter.down(name, result.detail)

        days = result.ssl_days_left
        if days is not None and days <= self.settings.ssl_warn_days:
            if name not in self.notified_ssl:
                self.notified_ssl.add(name)
                self.db.add_event(name, "ssl", f"{days} days left", ssl_days=days)
                await self.alerter.ssl_expiring(name, days)
        elif days is not None:
            self.notified_ssl.discard(name)

    async def run_cycle(self) -> None:
        """One full pass over every target plus a host sample."""
        targets = self.settings.targets
        results = await asyncio.gather(
            *(self.check(t) for t in targets), return_exceptions=True
        )
        for target, result in zip(targets, results):
            if isinstance(result, BaseException):
                log.warning("check for %s raised %s", target.name, result)
                result = CheckResult(up=False, detail=f"check error: {result}"[:200])
            self.db.add_result(target.name, target.kind, result)
            await self._handle_alerts(target, result)

        try:
            self.db.add_system(host_sample())
        except Exception as exc:  # pragma: no cover - psutil edge cases
            log.warning("host sample failed: %s", exc)

        self.cycles += 1
        if self.cycles % 60 == 1:
            self.db.prune(self.settings.history_days)

    async def loop(self) -> None:
        log.info("monitoring %d targets every %ds", len(self.settings.targets),
                 self.settings.interval_seconds)
        while True:
            try:
                await self.run_cycle()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # pragma: no cover - keep the loop alive
                log.exception("cycle failed: %s", exc)
            await asyncio.sleep(self.settings.interval_seconds)
