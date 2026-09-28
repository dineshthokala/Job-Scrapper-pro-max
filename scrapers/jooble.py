"""
Jooble scraper — https://in.jooble.org
Free meta-aggregator API that indexes Indeed, Glassdoor, ZipRecruiter,
Dice, Monster/Foundit, CareerJet, and hundreds of other job boards.

Requires a free API key from https://jooble.org/api/about
Set the env var JOOBLE_API_KEY or add it to your .env file.
"""

import hashlib
import os
import re

import requests

from scrapers.base import delay, make_job

# API key loaded from environment
JOOBLE_API_KEY = os.environ.get("JOOBLE_API_KEY", "")

# Use the India regional endpoint for Bangalore-focused results
_BASE_URL = "https://in.jooble.org/api"


def _query_jooble(keyword, page=1):
    """POST a search query to the Jooble API and return the raw JSON response."""
    if not JOOBLE_API_KEY:
        print("  [WARN] JOOBLE_API_KEY not set — skipping Jooble")
        return None

    url = f"{_BASE_URL}/{JOOBLE_API_KEY}"
    payload = {
        "keywords": keyword,
        "location": "Bengaluru",
        "page": page,
    }

    try:
        resp = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else "?"
        print(f"  [WARN] Jooble API HTTP {status}: {e}")
        return None
    except Exception as e:
        print(f"  [WARN] Jooble API request failed: {e}")
        return None


def _parse_jobs(data, keyword):
    """Convert Jooble API response into our standard job dicts."""
    jobs = []
    if not data or "jobs" not in data:
        return jobs

    for item in data["jobs"]:
        try:
            title = (item.get("title") or "").strip()
            company = (item.get("company") or "Jooble Employer").strip()
            location = (item.get("location") or "Bengaluru").strip()
            link = (item.get("link") or "").strip()
            jooble_id = item.get("id", "")

            # Generate a stable job ID from the link or Jooble ID
            if jooble_id:
                jid = str(jooble_id)
            else:
                jid = hashlib.md5(link.encode()).hexdigest()[:12]

            if not title or not link:
                continue

            # Clean HTML tags from title (Jooble sometimes returns <b> tags)
            title = re.sub(r"<[^>]+>", "", title).strip()

            job = make_job(
                prefix="jb",
                raw_id=jid,
                title=title,
                company=company,
                location=location,
                url=link,
                keyword=keyword,
                source="Jooble",
            )
            if job:
                jobs.append(job)

        except Exception as e:
            print(f"  [WARN] Jooble parse error: {e}")

    return jobs


def scrape_all_keywords(keywords, on_new_job=None):
    """Scrape Jooble for all configured keywords."""
    if not JOOBLE_API_KEY:
        print("  [SKIP] Jooble — no API key configured (set JOOBLE_API_KEY)")
        return []

    all_jobs = []

    for keyword in keywords:
        data = _query_jooble(keyword, page=1)
        if not data:
            print(f"  {keyword}: 0 job(s) [Jooble]")
            delay(1.0, 2.0)
            continue

        total = data.get("totalCount", 0)
        jobs = _parse_jobs(data, keyword)
        print(f"  {keyword}: {len(jobs)} job(s) from {total} total [Jooble]")

        for job in jobs:
            if on_new_job:
                on_new_job(job)
            else:
                all_jobs.append(job)

        delay(1.5, 3.0)

    return all_jobs
