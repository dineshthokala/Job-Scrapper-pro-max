"""
HiringCafe scraper — https://hiring.cafe
Newer job aggregator with clean public pages.
"""

import hashlib
import re

from scrapers.base import delay, fetch_soup, get_session, make_job, safe_text


def _build_urls(keyword):
    q = keyword.replace(" ", "+")
    return [
        f"https://hiring.cafe/jobs?q={q}&location=Bangalore",
        f"https://hiring.cafe/jobs?q={q}&location=Remote",
    ]


def _parse_jobs(soup, keyword, is_remote=False):
    jobs = []

    cards = (
        soup.select("div[class*='job-card']")
        or soup.select("div[class*='JobCard']")
        or soup.select("article[class*='job']")
        or soup.select("li[class*='job']")
        or soup.select("a[href*='/job/']")
    )

    for card in cards:
        try:
            if card.name == "a":
                link = card
            else:
                link = card.find("a", href=re.compile(r"/job/|/jobs/"))
            if not link:
                continue

            href = link.get("href", "")
            title = safe_text(link.find("h2") or link.find("h3") or link, "Unknown Title")
            if len(title) < 3:
                continue

            url = f"https://hiring.cafe{href}" if href.startswith("/") else href

            m = re.search(r"/job[s]?/([^/?#]+)", href)
            jid = m.group(1) if m else hashlib.md5(href.encode()).hexdigest()[:12]

            comp_el = card.find("span", class_=re.compile(r"company")) or card.find("p", class_=re.compile(r"company"))
            company = safe_text(comp_el, "Unknown Company")

            loc_el = card.find("span", class_=re.compile(r"location"))
            location = safe_text(loc_el, "Remote" if is_remote else "Bangalore")
            if is_remote and "remote" not in location.lower() and "wfh" not in location.lower():
                location = f"{location} (Remote)"

            job = make_job("hc", jid, title, company, location, url, keyword, "HiringCafe")
            if job:
                jobs.append(job)

        except Exception as e:
            print(f"  [WARN] HiringCafe parse error: {e}")

    return jobs


def scrape_all_keywords(keywords, on_new_job=None):
    all_jobs = []
    seen_ids = set()
    session = get_session()

    for keyword in keywords:
        kw_jobs = []
        for url in _build_urls(keyword):
            is_remote = "location=Remote" in url
            soup = fetch_soup(url, session=session)
            if not soup:
                continue

            jobs = _parse_jobs(soup, keyword, is_remote=is_remote)
            for job in jobs:
                if job["job_id"] not in seen_ids:
                    seen_ids.add(job["job_id"])
                    kw_jobs.append(job)
                    if on_new_job:
                        on_new_job(job)
                    else:
                        all_jobs.append(job)
            delay(1.0, 2.5)

        print(f"  {keyword}: {len(kw_jobs)} job(s) [HiringCafe] (Bangalore + Remote)")

    return all_jobs
