"""
Y Combinator (Work at a Startup) scraper — https://www.workatastartup.com
Public job listings from YC-backed startups.
"""

import hashlib
import re

from scrapers.base import delay, fetch_json, fetch_soup, get_session, make_job, safe_text


def _build_url(keyword):
    q = keyword.replace(" ", "+")
    return f"https://www.workatastartup.com/jobs?query={q}"


def _parse_html_jobs(soup, keyword):
    """Parse job cards from server-rendered HTML."""
    jobs = []
    cards = soup.select("div.job-listing") or soup.select("div[class*='job']") or soup.select("tr[class*='job']")

    for card in cards:
        try:
            link = card.find("a", href=re.compile(r"/jobs/\d+|/companies/"))
            if not link:
                continue

            href = link.get("href", "")
            title = safe_text(link, "Unknown Title")
            url = f"https://www.workatastartup.com{href}" if href.startswith("/") else href

            m = re.search(r"/jobs/(\d+)", href)
            jid = m.group(1) if m else hashlib.md5(href.encode()).hexdigest()[:12]

            # Company
            comp_el = card.find("a", href=re.compile(r"/companies/")) or card.find("span", class_=re.compile(r"company"))
            company = safe_text(comp_el, "Unknown Company")

            # Location
            loc_el = card.find("span", class_=re.compile(r"location")) or card.find("div", class_=re.compile(r"location"))
            location = safe_text(loc_el, "Remote")

            job = make_job("yc", jid, title, company, location, url, keyword, "YCombinator")
            if job:
                jobs.append(job)

        except Exception as e:
            print(f"  [WARN] YC parse error: {e}")

    return jobs


def scrape_all_keywords(keywords, on_new_job=None):
    all_jobs = []
    session = get_session()

    for keyword in keywords:
        url = _build_url(keyword)
        soup = fetch_soup(url, session=session)
        if not soup:
            continue

        jobs = _parse_html_jobs(soup, keyword)
        print(f"  {keyword}: {len(jobs)} job(s) [YCombinator]")

        for job in jobs:
            if on_new_job:
                on_new_job(job)
            else:
                all_jobs.append(job)

        delay(1.5, 3.0)

    return all_jobs
