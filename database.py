"""
database.py — SQLite persistence for jobs, application status, and scrape history.

Replaces the JSON-only ID tracking with a full relational store.
On first init, migrates any existing seen_jobs_*.json files.
"""

import csv
import io
import json
import os
import sqlite3
import threading
from datetime import datetime, timezone

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_DB_PATH = os.path.join(_BASE_DIR, "jobs.db")
_lock = threading.Lock()


# ── Connection helper ──────────────────────────────────────────────────

def _connect():
    conn = sqlite3.connect(_DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ── Schema & migration ────────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id      TEXT UNIQUE NOT NULL,
    title       TEXT NOT NULL,
    company     TEXT NOT NULL,
    location    TEXT DEFAULT '',
    url         TEXT DEFAULT '',
    keyword     TEXT DEFAULT '',
    source      TEXT DEFAULT '',
    status      TEXT DEFAULT 'new',
    notes       TEXT DEFAULT '',
    found_at    TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    updated_at  TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE IF NOT EXISTS scrape_runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at  TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    finished_at TEXT,
    sources     TEXT DEFAULT '',
    jobs_found  INTEGER DEFAULT 0,
    new_jobs    INTEGER DEFAULT 0,
    status      TEXT DEFAULT 'running'
);

CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_job_id ON jobs(job_id);
CREATE INDEX IF NOT EXISTS idx_jobs_found_at ON jobs(found_at);
"""


def init_db():
    """Create tables and migrate legacy JSON files."""
    with _lock:
        conn = _connect()
        conn.executescript(_SCHEMA)
        conn.commit()
        conn.close()

    # Migrate old JSON tracking files
    _migrate_json("seen_jobs_linkedin.json", "LinkedIn")
    _migrate_json("seen_jobs_others.json", "Others")


def _migrate_json(filename, label):
    """Import job IDs from a legacy seen_jobs JSON file."""
    path = os.path.join(_BASE_DIR, filename)
    if not os.path.exists(path):
        return
    try:
        with open(path, "r") as f:
            ids = json.load(f)
        if not ids:
            return

        with _lock:
            conn = _connect()
            migrated = 0
            for job_id in ids:
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO jobs (job_id, title, company, source, status) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (job_id, "(migrated)", "(migrated)", label, "new"),
                    )
                    migrated += 1
                except sqlite3.IntegrityError:
                    pass
            conn.commit()
            conn.close()
            if migrated:
                print(f"[DB] Migrated {migrated} job IDs from {filename}")

        # Rename the old file so we don't re-migrate
        backup = path + ".bak"
        if not os.path.exists(backup):
            os.rename(path, backup)
    except (json.JSONDecodeError, IOError) as e:
        print(f"[DB] Migration warning for {filename}: {e}")


# ── Job CRUD ───────────────────────────────────────────────────────────

def upsert_job(job: dict) -> bool:
    """
    Insert a new job or ignore if already exists.
    Returns True if the job was newly inserted (i.e. not seen before).
    """
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                "INSERT INTO jobs (job_id, title, company, location, url, keyword, source) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    job["job_id"],
                    job.get("title", "Unknown"),
                    job.get("company", "Unknown"),
                    job.get("location", ""),
                    job.get("url", ""),
                    job.get("keyword", ""),
                    job.get("source", ""),
                ),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()


def is_seen(job_id: str) -> bool:
    """Check if a job_id already exists in the database."""
    with _lock:
        conn = _connect()
        row = conn.execute("SELECT 1 FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        conn.close()
        return row is not None


def get_jobs(
    source=None, status=None, keyword=None, search=None,
    page=1, per_page=20, sort_by="found_at", sort_dir="desc",
):
    """Fetch jobs with optional filters, pagination, and sorting."""
    conditions = []
    params = []

    if source:
        conditions.append("source = ?")
        params.append(source)
    if status:
        conditions.append("status = ?")
        params.append(status)
    if keyword:
        conditions.append("keyword = ?")
        params.append(keyword)
    if search:
        conditions.append("(title LIKE ? OR company LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # Validate sort column to prevent injection
    valid_sorts = {"found_at", "title", "company", "source", "status", "updated_at"}
    if sort_by not in valid_sorts:
        sort_by = "found_at"
    direction = "ASC" if sort_dir.lower() == "asc" else "DESC"

    offset = (page - 1) * per_page

    with _lock:
        conn = _connect()

        # Total count
        count_row = conn.execute(f"SELECT COUNT(*) as cnt FROM jobs {where}", params).fetchone()
        total = count_row["cnt"]

        # Paginated results
        rows = conn.execute(
            f"SELECT * FROM jobs {where} ORDER BY {sort_by} {direction} LIMIT ? OFFSET ?",
            params + [per_page, offset],
        ).fetchall()
        conn.close()

    return {
        "jobs": [dict(r) for r in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
    }


def update_job_status(job_id: str, status: str = None, notes: str = None) -> bool:
    """Update the status and/or notes for a job."""
    updates = []
    params = []

    if status is not None:
        valid = {"new", "saved", "applied", "interviewing", "rejected", "offer"}
        if status not in valid:
            return False
        updates.append("status = ?")
        params.append(status)
    if notes is not None:
        updates.append("notes = ?")
        params.append(notes)

    if not updates:
        return False

    updates.append("updated_at = ?")
    params.append(datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    params.append(job_id)

    with _lock:
        conn = _connect()
        cursor = conn.execute(
            f"UPDATE jobs SET {', '.join(updates)} WHERE job_id = ?", params
        )
        conn.commit()
        changed = cursor.rowcount > 0
        conn.close()
        return changed


def get_stats():
    """Aggregate stats for the dashboard."""
    with _lock:
        conn = _connect()

        total = conn.execute("SELECT COUNT(*) as cnt FROM jobs").fetchone()["cnt"]

        # Jobs found in the last 24 hours
        today = conn.execute(
            "SELECT COUNT(*) as cnt FROM jobs "
            "WHERE found_at >= strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-1 day')"
        ).fetchone()["cnt"]

        # By source
        by_source = {}
        for row in conn.execute("SELECT source, COUNT(*) as cnt FROM jobs GROUP BY source"):
            by_source[row["source"] or "Unknown"] = row["cnt"]

        # By status
        by_status = {}
        for row in conn.execute("SELECT status, COUNT(*) as cnt FROM jobs GROUP BY status"):
            by_status[row["status"] or "new"] = row["cnt"]

        # Unique keywords
        keywords = [
            row[0] for row in conn.execute(
                "SELECT DISTINCT keyword FROM jobs WHERE keyword != '' ORDER BY keyword"
            ).fetchall()
        ]

        # Unique sources
        sources = [
            row[0] for row in conn.execute(
                "SELECT DISTINCT source FROM jobs WHERE source != '' ORDER BY source"
            ).fetchall()
        ]

        # Last scrape run
        last_run = conn.execute(
            "SELECT * FROM scrape_runs ORDER BY id DESC LIMIT 1"
        ).fetchone()

        conn.close()

    return {
        "total": total,
        "today": today,
        "by_source": by_source,
        "by_status": by_status,
        "keywords": keywords,
        "sources": sources,
        "last_run": dict(last_run) if last_run else None,
    }


# ── Scrape run tracking ───────────────────────────────────────────────

def log_scrape_run(sources: str) -> int:
    """Start a new scrape run and return its ID."""
    with _lock:
        conn = _connect()
        cursor = conn.execute(
            "INSERT INTO scrape_runs (sources) VALUES (?)", (sources,)
        )
        run_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return run_id


def finish_scrape_run(run_id: int, jobs_found: int, new_jobs: int, status: str = "completed"):
    """Finalize a scrape run with results."""
    with _lock:
        conn = _connect()
        conn.execute(
            "UPDATE scrape_runs SET finished_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now'), "
            "jobs_found = ?, new_jobs = ?, status = ? WHERE id = ?",
            (jobs_found, new_jobs, status, run_id),
        )
        conn.commit()
        conn.close()


# ── CSV export ─────────────────────────────────────────────────────────

def export_jobs_csv(source=None, status=None, keyword=None, search=None) -> str:
    """Export filtered jobs as a CSV string."""
    result = get_jobs(
        source=source, status=status, keyword=keyword, search=search,
        page=1, per_page=100000,  # all results
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Title", "Company", "Location", "Source", "Keyword", "Status", "URL", "Found At", "Notes"])
    for job in result["jobs"]:
        writer.writerow([
            job["title"], job["company"], job["location"], job["source"],
            job["keyword"], job["status"], job["url"], job["found_at"], job["notes"],
        ])
    return output.getvalue()
