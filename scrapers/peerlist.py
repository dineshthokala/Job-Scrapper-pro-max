"""
Peerlist scraper — https://peerlist.io
Developer community with job board.
"""

import hashlib
import re

from scrapers.base import delay, fetch_soup, get_session, make_job, safe_text


def _build_url(keyword):
    q = keyword.replace(" ", "+")
    return f"https://peerlist.io/jobs?search={q}"


def _parse_jobs(soup, keyword):
    jobs = []

    cards = (
        soup.select("div[class*='JobCard']")
        or soup.select("a[href*='/jobs/']")
        or soup.select("div[class*='job-card']")
        or soup.select("article")
    )

    for card in cards:
        try:
            if card.name == "a":
                link = card
            else:
                link = card.find("a", href=re.compile(r"/jobs/"))
            if not link:
                continue

            href = link.get("href", "")
            title = safe_text(link.find("h3") or link.find("h2") or link.find("p") or link, "")
            if not title or len(title) < 3:
                continue

            url = f"https://peerlist.io{href}" if href.startswith("/") else href

            m = re.search(r"/jobs/([^/?#]+)", href)
            jid = m.group(1) if m else hashlib.md5(href.encode()).hexdigest()[:12]

            comp_el = card.find("span", class_=re.compile(r"company|org"))
            company = safe_text(comp_el, "Unknown Company")

            loc_el = card.find("span", class_=re.compile(r"location"))
            location = safe_text(loc_el, "Remote")

            job = make_job("pl", jid, title, company, location, url, keyword, "Peerlist")
            if job:
                jobs.append(job)

        except Exception as e:
            print(f"  [WARN] Peerlist parse error: {e}")

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
        print(f"  {keyword}: {len(jobs)} job(s) [Peerlist]")

        for job in jobs:
            if on_new_job:
                on_new_job(job)
            else:
                all_jobs.append(job)

        delay(1.5, 3.0)

    return all_jobs
