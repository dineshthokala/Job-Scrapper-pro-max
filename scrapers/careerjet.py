"""
CareerJet India scraper — https://www.careerjet.co.in
Simple server-rendered HTML, works well with plain requests.
"""

import hashlib
import re

from scrapers.base import delay, fetch_soup, get_session, make_job, safe_text


def _build_urls(keyword, page=1):
    q = keyword.replace(" ", "+")
    return [
        f"https://www.careerjet.co.in/search/jobs?s={q}&l=bangalore&radius=30&p={page}",
        f"https://www.careerjet.co.in/search/jobs?s={q}&l=remote&p={page}",
    ]


def _parse_jobs(soup, keyword):
    jobs = []
    cards = soup.select("article.job")
    if not cards:
        cards = soup.select("li.job")
    if not cards:
        cards = soup.select("div.job")

    for card in cards:
        try:
            # Title + URL
            link = card.select_one("header h2 a") or card.find("a", class_="title")
            if not link:
                continue
            title = safe_text(link, "Unknown Title")
            href = link.get("href", "")
            url = f"https://www.careerjet.co.in{href}" if href.startswith("/") else href

            # Job ID from URL
            m = re.search(r"/job/([^/]+)", href)
            jid = m.group(1) if m else hashlib.md5(href.encode()).hexdigest()[:12]

            # Company
            comp_el = card.select_one("p.company") or card.select_one("span.company")
            company = safe_text(comp_el, "Unknown Company")

            # Location
            loc_el = card.select_one("ul.location li") or card.select_one("span.location")
            location = safe_text(loc_el, "Bangalore")

            job = make_job("cj", jid, title, company, location, url, keyword, "CareerJet")
            if job:
                jobs.append(job)

        except Exception as e:
            print(f"  [WARN] CareerJet parse error: {e}")

    return jobs


def scrape_all_keywords(keywords, on_new_job=None):
    all_jobs = []
    seen_ids = set()
    session = get_session()

    for keyword in keywords:
        kw_jobs = []
        for url in _build_urls(keyword):
            soup = fetch_soup(url, session=session)
            if not soup:
                continue

            jobs = _parse_jobs(soup, keyword)
            for job in jobs:
                if job["job_id"] not in seen_ids:
                    seen_ids.add(job["job_id"])
                    kw_jobs.append(job)
                    if on_new_job:
                        on_new_job(job)
                    else:
                        all_jobs.append(job)
            delay(1.0, 2.0)

        print(f"  {keyword}: {len(kw_jobs)} job(s) [CareerJet] (Bangalore + Remote)")

    return all_jobs
