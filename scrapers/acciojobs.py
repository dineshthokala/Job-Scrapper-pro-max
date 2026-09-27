"""
AccioJob scraper — https://www.acciojob.com
Indian job platform focused on tech freshers.
"""

import hashlib
import re

from scrapers.base import delay, fetch_soup, get_session, make_job, safe_text


def _build_url(keyword):
    q = keyword.replace(" ", "+")
    return f"https://www.acciojob.com/jobs?search={q}&location=Bangalore"


def _parse_jobs(soup, keyword):
    jobs = []

    cards = (
        soup.select("div[class*='job-card']")
        or soup.select("div[class*='JobCard']")
        or soup.select("a[href*='/job/']")
        or soup.select("div[class*='listing']")
    )

    for card in cards:
        try:
            if card.name == "a":
                link = card
            else:
                link = card.find("a", href=re.compile(r"/job[s]?/"))
            if not link:
                continue

            href = link.get("href", "")
            title = safe_text(link.find("h2") or link.find("h3") or link.find("p") or link, "Unknown Title")
            if len(title) < 3:
                continue

            url = f"https://www.acciojob.com{href}" if href.startswith("/") else href

            m = re.search(r"/job[s]?/([^/?#]+)", href)
            jid = m.group(1) if m else hashlib.md5(href.encode()).hexdigest()[:12]

            comp_el = card.find("span", class_=re.compile(r"company"))
            company = safe_text(comp_el, "Unknown Company")

            loc_el = card.find("span", class_=re.compile(r"location"))
            location = safe_text(loc_el, "Bangalore")

            job = make_job("aj", jid, title, company, location, url, keyword, "AccioJobs")
            if job:
                jobs.append(job)

        except Exception as e:
            print(f"  [WARN] AccioJobs parse error: {e}")

    return jobs


def scrape_all_keywords(keywords, on_new_job=None):
    all_jobs = []
    session = get_session()

    for keyword in keywords:
        url = _build_url(keyword)
        soup = fetch_soup(url, session=session)
        if not soup:
            continue

        jobs = _parse_jobs(soup, keyword)
        print(f"  {keyword}: {len(jobs)} job(s) [AccioJobs]")

        for job in jobs:
            if on_new_job:
                on_new_job(job)
            else:
                all_jobs.append(job)

        delay(1.5, 3.0)

    return all_jobs
