"""SQLite cache of repo-level derived scores. Not a stargazer identity store."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


def default_path() -> Path:
    return Path.home() / ".cache" / "repo-viability" / "cache.sqlite"


def connect(path: Path | None = None) -> sqlite3.Connection:
    path = path or default_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS repo_scans (
            repo TEXT PRIMARY KEY,
            scanned_at TEXT NOT NULL,
            report_json TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def get(conn: sqlite3.Connection, repo: str, max_age_hours: int) -> dict | None:
    row = conn.execute(
        "SELECT scanned_at, report_json FROM repo_scans WHERE repo = ?",
        (repo,),
    ).fetchone()
    if not row:
        return None
    scanned_at = datetime.fromisoformat(row[0])
    if scanned_at.tzinfo is None:
        scanned_at = scanned_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - scanned_at > timedelta(hours=max_age_hours):
        return None
    return json.loads(row[1])


def put(conn: sqlite3.Connection, repo: str, report: dict) -> None:
    # Persist the public report only. Sample account logins are stripped first
    # by the scorer so this table cannot become a resale identity database.
    conn.execute(
        """
        INSERT INTO repo_scans (repo, scanned_at, report_json)
        VALUES (?, ?, ?)
        ON CONFLICT(repo) DO UPDATE SET
            scanned_at = excluded.scanned_at,
            report_json = excluded.report_json
        """,
        (repo, datetime.now(timezone.utc).isoformat(), json.dumps(report)),
    )
    conn.commit()
