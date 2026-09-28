"""
scrapers/base.py — Shared HTTP session, headers, and parsing utilities
for all lightweight (non-Selenium) scrapers.
"""

import random
import re
import sys
import os
import time

import requests
from bs4 import BeautifulSoup

# Allow imports from parent directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from driver import passes_filters  # noqa: E402

# ── User-Agent rotation ───────────────────────────────────────────────

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
]


def get_session():
    """Create a requests session with realistic browser headers."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": random.choice(_USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    })
    return s


def fetch_soup(url, session=None, timeout=15):
    """Fetch a URL and return a BeautifulSoup object, or None on error."""
    s = session or get_session()
    try:
        resp = s.get(url, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "lxml")
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 403:
            print(f"  [INFO] Cloudflare/Bot-shield blocked request (403), skipping {url[:45]}...")
        else:
            print(f"  [WARN] HTTP {e}")
        return None
    except Exception as e:
        print(f"  [WARN] HTTP fetch failed: {e}")
        return None


def fetch_json(url, session=None, timeout=15, params=None, headers=None):
    """Fetch JSON from a URL, return dict or None on error."""
    s = session or get_session()
    if headers:
        s.headers.update(headers)
    else:
        s.headers["Accept"] = "application/json"
    try:
        resp = s.get(url, timeout=timeout, params=params, allow_redirects=True)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 403:
            print(f"  [INFO] Cloudflare/Bot-shield blocked JSON request (403), skipping {url[:45]}...")
        else:
            print(f"  [WARN] JSON HTTP {e}")
        return None
    except Exception as e:
        print(f"  [WARN] JSON fetch failed: {e}")
        return None



def post_json(url, payload, session=None, timeout=20):
    """POST JSON to a URL, return response dict or None."""
    s = session or get_session()
    s.headers["Accept"] = "application/json"
    s.headers["Content-Type"] = "application/json"
    try:
        resp = s.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  [WARN] JSON POST failed: {e}")
        return None


def delay(min_s=1.0, max_s=3.0):
    """Random delay to be polite."""
    time.sleep(random.uniform(min_s, max_s))


def safe_text(el, default=""):
    """Safely get stripped text from a BS4 element."""
    return el.get_text(strip=True) if el else default


def make_job(job_id_prefix, raw_id, title, company, location, url, keyword, source):
    """Create a standardised job dict, filtering through passes_filters."""
    passes, reason = passes_filters(title, company, location=location)
    if not passes:
        print(f"    [SKIP] {reason}")
        return None
    if url and not url.startswith("http"):
        url = f"https://{url.lstrip('/')}"
    return {
        "job_id": f"{job_id_prefix}_{raw_id}",
        "title": title,
        "company": company,
        "location": location or "",
        "url": url or "",
        "keyword": keyword,
        "source": source,
    }
