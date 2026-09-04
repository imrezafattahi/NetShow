"""Telegram notifications. Silently disabled when no token is configured."""

from __future__ import annotations

import logging

import httpx

from .config import Settings

log = logging.getLogger("netshow.alerts")


class Alerter:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def send(self, text: str) -> bool:
        if not self.settings.telegram_enabled:
            log.info("alert (not delivered, Telegram disabled): %s", text)
            return False
        url = f"https://api.telegram.org/bot{self.settings.telegram_token}/sendMessage"
        payload = {
            "chat_id": self.settings.telegram_chat_id,
            "text": text,
            "disable_web_page_preview": True,
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
            response.raise_for_status()
            return True
        except httpx.HTTPError as exc:
            log.warning("Telegram delivery failed: %s", exc)
            return False

    async def down(self, target: str, detail: str | None) -> None:
        await self.send(f"\U0001f534 {target} is down\n{detail or 'no further detail'}")

    async def up(self, target: str) -> None:
        await self.send(f"\U0001f7e2 {target} is back online")

    async def ssl_expiring(self, target: str, days: int) -> None:
        await self.send(f"\U0001f7e1 {target}: TLS certificate expires in {days} days")
