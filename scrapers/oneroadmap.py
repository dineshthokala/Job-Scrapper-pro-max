"""
OneRoadmap scraper — https://www.oneroadmap.io
Curated job board for tech roles, internships, and entry-level developers.
"""

import re
import urllib.parse
from scrapers.base import delay, fetch_soup, get_session, make_job


def _search_oneroadmap(keyword, session):
    """Fetch jobs from OneRoadmap search."""
    search_term = "flutter" if "flutter" in keyword.lower() else keyword.split()[0]
    encoded_kw = urllib.parse.quote(search_term)
    url = f"https://www.oneroadmap.io/jobs?q={encoded_kw}"
    soup = fetch_soup(url, session=session)
    if not soup:
        return []

    jobs = []
    seen_ids = set()

    for a in soup.find_all("a", href=re.compile(r"/jobs/([a-f0-9]+)")):
        try:
            href = a.get("href", "")
            m = re.search(r"/jobs/([a-f0-9]+)", href)
            if not m:
                continue
            jid = m.group(1)
            if jid in seen_ids:
                continue

            # Skip button labels
            text = a.get_text(strip=True)
            if text in ["View role", "Apply", "Save", "Not interested"]:
                continue

            card = a.find_parent(
                lambda el: el.name == "div"
                and (len(el.find_all("button")) > 0 or len(el.find_all("a")) > 1)
            )

            title = text or "Flutter Developer"
            company = "Unknown Company"
            location = "Bengaluru / Remote"

            if card:
                strings = list(card.stripped_strings)
                if len(strings) >= 4:
                    company = strings[0]
                    location = strings[1]
                    # Title is usually strings[3] or the link text
                    if text not in ["View role", "Apply"]:
                        title = text

            job_url = f"https://www.oneroadmap.io/jobs/{jid}"
            job = make_job("orm", jid, title, company, location, job_url, keyword, "OneRoadmap")
            if job:
                seen_ids.add(jid)
                jobs.append(job)

        except Exception as e:
            print(f"  [WARN] OneRoadmap parse error: {e}")

    return jobs


def scrape_all_keywords(keywords, on_new_job=None):
    all_jobs = []
    session = get_session()

    for keyword in keywords:
        jobs = _search_oneroadmap(keyword, session)
        print(f"  {keyword}: {len(jobs)} job(s) [OneRoadmap]")

        for job in jobs:
            if on_new_job:
                on_new_job(job)
            else:
                all_jobs.append(job)

        delay(1.0, 2.5)

    return all_jobs
