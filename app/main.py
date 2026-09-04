"""FastAPI application: JSON API plus the bundled dashboard."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from . import __version__
from .config import Settings, load_settings
from .db import Database, utcnow
from .scheduler import Monitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

STATIC_DIR = Path(__file__).parent / "static"
EMPTY_SYSTEM = {
    "cpu": 0.0, "ram": 0.0, "ram_total_gb": 0.0, "disk": 0.0,
    "disk_total_gb": 0.0, "net_recv_kbps": 0.0, "net_sent_kbps": 0.0,
}


def build_snapshot(settings: Settings, db: Database) -> dict[str, Any]:
    """Everything the dashboard needs in a single response."""
    targets: list[dict[str, Any]] = []
    for target in settings.targets:
        latest = db.latest(target.name)
        targets.append(
            {
                "name": target.name,
                "kind": target.kind,
                "host": target.address,
                "up": bool(latest["up"]) if latest else None,
                "latency_ms": latest["latency_ms"] if latest else None,
                "packet_loss": latest["packet_loss"] if latest else None,
                "status_code": latest["status_code"] if latest else None,
                "ssl_days_left": latest["ssl_days"] if latest else None,
                "detail": latest["detail"] if latest else None,
                "last_check": latest["ts"] if latest else None,
                "uptime_24h": db.uptime(target.name),
                "history": db.history(target.name, hours=6, limit=36),
            }
        )

    system = db.latest_system() or dict(EMPTY_SYSTEM)
    system.pop("id", None)
    system.pop("ts", None)
    return {
        "generated_at": utcnow(),
        "interval_seconds": settings.interval_seconds,
        "system": system,
        "targets": targets,
        "events": db.events(limit=25),
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    db = Database(settings.db_path)
    db.connect()
    monitor = Monitor(settings, db)
    app.state.settings, app.state.db, app.state.monitor = settings, db, monitor

    task: asyncio.Task | None = None
    if os.getenv("NETSHOW_DISABLE_SCHEDULER") != "1":
        task = asyncio.create_task(monitor.loop())
    try:
        yield
    finally:
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        db.close()


app = FastAPI(
    title="NetShow",
    version=__version__,
    summary="Ping, HTTP, TLS and host monitoring in one small service",
    lifespan=lifespan,
)


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": __version__,
        "targets": len(app.state.settings.targets),
        "cycles": app.state.monitor.cycles,
    }


@app.get("/api/status")
async def status() -> dict[str, Any]:
    return build_snapshot(app.state.settings, app.state.db)


@app.get("/api/history")
async def history(target: str, hours: float = Query(24, gt=0, le=720)) -> dict[str, Any]:
    known = {t.name for t in app.state.settings.targets}
    if target not in known:
        raise HTTPException(status_code=404, detail=f"unknown target: {target}")
    return {
        "target": target,
        "hours": hours,
        "samples": app.state.db.history(target, hours=hours, limit=2000),
    }


@app.get("/api/events")
async def events(limit: int = Query(50, ge=1, le=500)) -> dict[str, Any]:
    return {"events": app.state.db.events(limit=limit)}


@app.post("/api/run")
async def run_now() -> dict[str, Any]:
    await app.state.monitor.run_cycle()
    return {"status": "done", "cycles": app.state.monitor.cycles}


if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="dashboard")
