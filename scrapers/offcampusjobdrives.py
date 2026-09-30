"""
OffCampusJobDrives scraper — https://offcampusjobdrives.com
Scrapes off-campus recruitment drives, fresher roles, and internships for Flutter/Mobile developers.
Utilises WordPress REST API endpoints for high performance and reliability.
"""

import html
import re
from bs4 import BeautifulSoup

from scrapers.base import delay, fetch_json, get_session, make_job


_BASE_API = "https://offcampusjobdrives.com/wp-json/wp/v2/posts"

_RELEVANT_KEYWORDS = ["flutter", "dart", "mobile", "android", "ios"]


def _extract_post_details(post):
    """
    Extract structured company, role, location, and direct application URL
    from a WordPress post item.
    """
    raw_id = str(post.get("id"))
    post_title = html.unescape(post.get("title", {}).get("rendered", "")).strip()
    content_html = post.get("content", {}).get("rendered", "")
    post_url = post.get("link", "").strip()

    soup = BeautifulSoup(content_html, "html.parser")

    company = ""
    role = ""
    location = ""

    # Parse metadata fields often listed as <p><strong>Field :</strong> Value</p>
    for el in soup.find_all(["p", "li"]):
        text = el.get_text(strip=True)
        m = re.match(r"^(Company|Role|Job Role|Location)\s*[:\-]\s*(.*)$", text, re.I)
        if m:
            key = m.group(1).lower()
            val = m.group(2).strip()
            if "company" in key and not company:
                company = val
            elif "role" in key and not role:
                role = val
            elif "location" in key and not location:
                location = val

    # Fallback company extraction from post title (e.g., "Refyne Off Campus Hiring...")
    if not company:
        m = re.match(r"^([A-Za-z0-9\s\.\&\+\-]+?)\s+(?:Off Campus|Recruitment|Hiring|Career)", post_title, re.I)
        if m:
            company = m.group(1).strip()
        else:
            company = "OffCampusJobDrives"

    # Fallback role
    if not role:
        role = post_title

    # Check if remote / WFH is mentioned in content
    is_remote = bool(re.search(r"\b(remote|work from home|wfh|telecommute|virtual)\b", f"{post_title} {content_html}", re.I))

    # Fallback location
    if not location:
        location = "Bengaluru / Remote, India"
    elif is_remote and "remote" not in location.lower() and "wfh" not in location.lower():
        location = f"{location} (Remote)"

    # Extract direct application link if present (Greenhouse, GreytHR, Oracle Cloud, Ashby, etc.)
    apply_url = post_url
    for a in soup.find_all("a"):
        href = (a.get("href") or "").strip()
        if not href or not href.startswith("http"):
            continue
        href_lower = href.lower()
        # Skip community channels & social sharing links
        if any(skip in href_lower for skip in [
            "telegram", "whatsapp", "offcampusjobdrives.com",
            "facebook.com", "instagram.com", "twitter.com", "x.com",
            "linkedin.com/sharing", "linkedin.com/in", "youtube.com"
        ]):
            continue
        apply_url = href
        break

    return {
        "raw_id": raw_id,
        "post_title": post_title,
        "role": role,
        "company": company,
        "location": location,
        "apply_url": apply_url,
        "content_html": content_html,
    }


def _process_posts(posts, keyword, seen_ids, on_new_job=None):
    """Process a batch of WP REST API posts, apply filters, and yield job dicts."""
    found_jobs = []

    for post in posts:
        pid = str(post.get("id"))
        if pid in seen_ids:
            continue

        try:
            details = _extract_post_details(post)

            # Ensure the post is actually related to Flutter/Dart/Mobile
            post_full_text = f"{details['post_title']} {details['role']} {details['content_html']}".lower()
            if not any(re.search(r"\b" + re.escape(term) + r"\b", post_full_text) for term in _RELEVANT_KEYWORDS):
                continue

            # Use role if it contains key domain terms, else full post title
            role_lower = details["role"].lower()
            if any(re.search(r"\b" + re.escape(term) + r"\b", role_lower) for term in _RELEVANT_KEYWORDS):
                title_to_use = details["role"]
            else:
                title_to_use = details["post_title"]

            job = make_job(
                job_id_prefix="ocjd",
                raw_id=details["raw_id"],
                title=title_to_use,
                company=details["company"],
                location=details["location"],
                url=details["apply_url"],
                keyword=keyword,
                source="OffCampusJobDrives",
            )

            seen_ids.add(pid)

            if job:
                found_jobs.append(job)
                if on_new_job:
                    on_new_job(job)

        except Exception as e:
            print(f"  [WARN] OffCampusJobDrives parse error for post {pid}: {e}")

    return found_jobs


def scrape_all_keywords(keywords, on_new_job=None):
    """
    Scrape jobs from OffCampusJobDrives via WordPress REST API.
    Searches relevant keywords and checks recent postings.
    """
    all_jobs = []
    seen_ids = set()
    session = get_session()

    # Determine unique search terms
    search_terms = set()
    for kw in keywords:
        kw_lower = kw.lower()
        if "flutter" in kw_lower:
            search_terms.add("flutter")
        elif "dart" in kw_lower:
            search_terms.add("dart")
        elif "mobile" in kw_lower:
            search_terms.add("mobile")
        else:
            search_terms.add(kw.split()[0])

    # Always ensure flutter is searched
    search_terms.add("flutter")

    # 1. Search by each relevant term
    for term in search_terms:
        url = f"{_BASE_API}?search={term}&per_page=15"
        posts = fetch_json(url, session=session)
        if posts and isinstance(posts, list):
            jobs = _process_posts(posts, f"{term.capitalize()} Developer", seen_ids, on_new_job=on_new_job)
            all_jobs.extend(jobs)
        delay(1.0, 2.0)

    # 2. Check the latest published posts to catch brand new postings
    recent_url = f"{_BASE_API}?per_page=15"
    recent_posts = fetch_json(recent_url, session=session)
    if recent_posts and isinstance(recent_posts, list):
        jobs = _process_posts(recent_posts, "Flutter Developer", seen_ids, on_new_job=on_new_job)
        all_jobs.extend(jobs)

    print(f"  OffCampusJobDrives: {len(all_jobs)} candidate job(s) found.")
    return all_jobs
