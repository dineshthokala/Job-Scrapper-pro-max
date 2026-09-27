"""
Otta scraper — https://app.otta.com
Curated tech job platform. Public job listings available via search.
"""

import hashlib
import re

from scrapers.base import delay, fetch_soup, get_session, make_job, safe_text


def _build_url(keyword):
    q = keyword.replace(" ", "+")
    return f"https://app.otta.com/jobs?search={q}"


def _parse_jobs(soup, keyword):
    jobs = []

    cards = (
        soup.select("div[class*='JobCard']")
        or soup.select("a[href*='/jobs/']")
        or soup.select("div[data-testid*='job']")
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
            title_el = link.find("h2") or link.find("h3") or link.find("span", class_=re.compile(r"title"))
            title = safe_text(title_el)
            if not title:
                title = safe_text(link)
            if not title or len(title) < 3:
                continue

            url = f"https://app.otta.com{href}" if href.startswith("/") else href

            m = re.search(r"/jobs/([^/?#]+)", href)
            jid = m.group(1) if m else hashlib.md5(href.encode()).hexdigest()[:12]

            comp_el = card.find("span", class_=re.compile(r"company")) or card.find("p")
            company = safe_text(comp_el, "Unknown Company")

            loc_el = card.find("span", class_=re.compile(r"location"))
            location = safe_text(loc_el, "Remote")

            job = make_job("otta", jid, title, company, location, url, keyword, "Otta")
            if job:
                jobs.append(job)

        except Exception as e:
            print(f"  [WARN] Otta parse error: {e}")

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
        print(f"  {keyword}: {len(jobs)} job(s) [Otta]")

        for job in jobs:
            if on_new_job:
                on_new_job(job)
            else:
                all_jobs.append(job)

        delay(2.0, 4.0)

    return all_jobs
