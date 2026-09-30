"""
Instahyre scraper — https://www.instahyre.com
Tech-focused job platform popular with Indian startups.
"""

import hashlib
import re

from scrapers.base import delay, fetch_soup, get_session, make_job, safe_text


def _build_urls(keyword):
    q = keyword.replace(" ", "%20")
    return [
        f"https://www.instahyre.com/search-jobs/?search={q}&location=Bengaluru",
        f"https://www.instahyre.com/search-jobs/?search={q}&location=Work%20from%20home",
    ]


def _parse_jobs(soup, keyword, is_remote=False):
    jobs = []

    cards = (
        soup.select("div.opportunity-card")
        or soup.select("div[class*='opportunity']")
        or soup.select("div.job-card")
        or soup.select("div[class*='job-listing']")
    )

    for card in cards:
        try:
            # Title + link
            link = (
                card.find("a", href=re.compile(r"/job/|/opportunity/"))
                or card.select_one("h3 a")
                or card.select_one("h2 a")
                or card.find("a")
            )
            if not link:
                continue

            title = safe_text(link, "Unknown Title")
            href = link.get("href", "")
            url = f"https://www.instahyre.com{href}" if href.startswith("/") else href

            m = re.search(r"(?:/job/|/opportunity/)(\d+)", href)
            jid = m.group(1) if m else hashlib.md5(href.encode()).hexdigest()[:12]

            # Company
            comp_el = (
                card.select_one("div.company-name")
                or card.find("span", class_=re.compile(r"company"))
                or card.select_one("p.company")
            )
            company = safe_text(comp_el, "Unknown Company")

            # Location
            loc_el = card.find("span", class_=re.compile(r"location")) or card.find("div", class_=re.compile(r"location"))
            location = safe_text(loc_el, "Remote" if is_remote else "Bengaluru")
            if is_remote and "remote" not in location.lower() and "wfh" not in location.lower():
                location = f"{location} (Remote)"

            job = make_job("ih", jid, title, company, location, url, keyword, "Instahyre")
            if job:
                jobs.append(job)

        except Exception as e:
            print(f"  [WARN] Instahyre parse error: {e}")

    return jobs


def scrape_all_keywords(keywords, on_new_job=None):
    all_jobs = []
    seen_ids = set()
    session = get_session()

    for keyword in keywords:
        kw_jobs = []
        for url in _build_urls(keyword):
            is_remote = "Work%20from%20home" in url
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
            delay(1.5, 3.0)

        print(f"  {keyword}: {len(kw_jobs)} job(s) [Instahyre] (Bengaluru + Remote)")

    return all_jobs
