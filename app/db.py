"""SQLite storage. One file, three tables, no ORM."""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS results (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    target      TEXT    NOT NULL,
    kind        TEXT    NOT NULL,
    ts          TEXT    NOT NULL,
    up          INTEGER NOT NULL,
    latency_ms  REAL,
    packet_loss REAL,
    status_code INTEGER,
    ssl_days    INTEGER,
    detail      TEXT
);
CREATE INDEX IF NOT EXISTS idx_results_target_ts ON results (target, ts);

CREATE TABLE IF NOT EXISTS events (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    target   TEXT    NOT NULL,
    ts       TEXT    NOT NULL,
    kind     TEXT    NOT NULL,
    message  TEXT,
    ssl_days INTEGER
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events (ts);

CREATE TABLE IF NOT EXISTS system_samples (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            TEXT NOT NULL,
    cpu           REAL,
    ram           REAL,
    ram_total_gb  REAL,
    disk          REAL,
    disk_total_gb REAL,
    net_recv_kbps REAL,
    net_sent_kbps REAL
);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _since(hours: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat(timespec="seconds")


class Database:
    """Thin synchronous wrapper. Writes are serialised with a lock."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()
        self._conn: sqlite3.Connection | None = None

    # -- lifecycle ---------------------------------------------------------
    def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Database.connect() was never called")
        return self._conn

    # -- writes ------------------------------------------------------------
    def add_result(self, target: str, kind: str, result: Any) -> None:
        with self._lock:
            self.conn.execute(
                "INSERT INTO results (target, kind, ts, up, latency_ms, packet_loss,"
                " status_code, ssl_days, detail) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    target,
                    kind,
                    utcnow(),
                    int(bool(result.up)),
                    result.latency_ms,
                    result.packet_loss,
                    result.status_code,
                    result.ssl_days_left,
                    result.detail,
                ),
            )
            self.conn.commit()

    def add_system(self, sample: dict[str, float]) -> None:
        with self._lock:
            self.conn.execute(
                "INSERT INTO system_samples (ts, cpu, ram, ram_total_gb, disk,"
                " disk_total_gb, net_recv_kbps, net_sent_kbps) VALUES (?,?,?,?,?,?,?,?)",
                (
                    utcnow(),
                    sample.get("cpu"),
                    sample.get("ram"),
                    sample.get("ram_total_gb"),
                    sample.get("disk"),
                    sample.get("disk_total_gb"),
                    sample.get("net_recv_kbps"),
                    sample.get("net_sent_kbps"),
                ),
            )
            self.conn.commit()

    def add_event(self, target: str, kind: str, message: str | None = None,
                  ssl_days: int | None = None) -> None:
        with self._lock:
            self.conn.execute(
                "INSERT INTO events (target, ts, kind, message, ssl_days) VALUES (?,?,?,?,?)",
                (target, utcnow(), kind, message, ssl_days),
            )
            self.conn.commit()

    def prune(self, days: int) -> int:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")
        with self._lock:
            cur = self.conn.execute("DELETE FROM results WHERE ts < ?", (cutoff,))
            self.conn.execute("DELETE FROM system_samples WHERE ts < ?", (cutoff,))
            self.conn.execute("DELETE FROM events WHERE ts < ?", (cutoff,))
            self.conn.commit()
            return cur.rowcount or 0

    # -- reads -------------------------------------------------------------
    def latest(self, target: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM results WHERE target = ? ORDER BY id DESC LIMIT 1", (target,)
        ).fetchone()
        return dict(row) if row else None

    def history(self, target: str, hours: float = 6, limit: int = 60) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT ts, up, latency_ms, packet_loss, status_code FROM results"
            " WHERE target = ? AND ts >= ? ORDER BY id DESC LIMIT ?",
            (target, _since(hours), limit),
        ).fetchall()
        return [dict(r) | {"up": bool(r["up"])} for r in reversed(rows)]

    def uptime(self, target: str, hours: float = 24) -> float | None:
        row = self.conn.execute(
            "SELECT COUNT(*) AS n, SUM(up) AS ok FROM results WHERE target = ? AND ts >= ?",
            (target, _since(hours)),
        ).fetchone()
        if not row or not row["n"]:
            return None
        return round((row["ok"] or 0) * 100.0 / row["n"], 2)

    def latest_system(self) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT * FROM system_samples ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

    def events(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT target, ts, kind, message, ssl_days FROM events ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
