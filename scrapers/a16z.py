"""
a16z Job Board scraper — https://jobs.a16z.com
Scrapes job openings across Andreessen Horowitz portfolio companies.
"""

import re
import urllib.parse
from scrapers.base import delay, fetch_soup, get_session, make_job


def _search_a16z(keyword, session):
    """Fetch jobs from a16z job board for a keyword."""
    encoded_kw = urllib.parse.quote(keyword)
    url = f"https://jobs.a16z.com/jobs?q={encoded_kw}"
    soup = fetch_soup(url, session=session)
    if not soup:
        return []

    jobs = []
    seen_ids = set()

    for a in soup.find_all("a", href=re.compile(r"/jobs/[^/]+/([a-f0-9-]+)--")):
        try:
            href = a.get("href", "")
            m = re.search(r"/jobs/([^/]+)/([a-f0-9-]+)--", href)
            if not m:
                continue

            company_slug = m.group(1)
            jid = m.group(2)
            if jid in seen_ids:
                continue

            title = a.get_text(strip=True)
            if not title or len(title) < 3:
                continue

            company = company_slug.replace("-", " ").title()
            job_url = f"https://jobs.a16z.com{href}"
            location = "Remote / Global"

            job = make_job("a16z", jid, title, company, location, job_url, keyword, "jobs.a16z")
            if job:
                seen_ids.add(jid)
                jobs.append(job)

        except Exception as e:
            print(f"  [WARN] a16z parse error: {e}")

    return jobs


def scrape_all_keywords(keywords, on_new_job=None):
    all_jobs = []
    session = get_session()

    for keyword in keywords:
        jobs = _search_a16z(keyword, session)
        print(f"  {keyword}: {len(jobs)} job(s) [jobs.a16z]")

        for job in jobs:
            if on_new_job:
                on_new_job(job)
            else:
                all_jobs.append(job)

        delay(1.0, 2.5)

    return all_jobs
