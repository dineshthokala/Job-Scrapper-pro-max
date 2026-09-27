"""
Arc.dev scraper — https://arc.dev
Remote-focused developer job board with public listings.
"""

import hashlib
import re

from scrapers.base import delay, fetch_soup, get_session, make_job, safe_text


def _build_url(keyword):
    q = keyword.lower().replace(" ", "-")
    return f"https://arc.dev/remote-jobs/{q}"


def _parse_jobs(soup, keyword):
    jobs = []

    # Arc uses job cards in list
    cards = soup.select("a[href*='/remote-jobs/']")
    if not cards:
        cards = soup.select("div.job-card")
    if not cards:
        cards = soup.select("article")

    seen_urls = set()
    for card in cards:
        try:
            # Get the link — might be the card itself
            if card.name == "a":
                link = card
            else:
                link = card.find("a", href=re.compile(r"/remote-jobs/"))
            if not link:
                continue

            href = link.get("href", "")
            if not href or href in seen_urls:
                continue
            # Skip category/filter links
            if re.match(r"^/remote-jobs/[a-z-]+/?$", href) and "/" not in href.strip("/").split("/", 1)[-1]:
                continue
            seen_urls.add(href)

            url = f"https://arc.dev{href}" if href.startswith("/") else href

            # Title
            title_el = link.find("h2") or link.find("h3") or link.find("span", class_=re.compile(r"title"))
            title = safe_text(title_el)
            if not title:
                title = safe_text(link)
            if not title or len(title) < 3:
                continue

            # Job ID
            m = re.search(r"/remote-jobs/([^/?#]+)", href)
            jid = m.group(1) if m else hashlib.md5(href.encode()).hexdigest()[:12]

            # Company
            comp_el = card.find("span", class_=re.compile(r"company")) or card.find("p")
            company = safe_text(comp_el, "Unknown Company")

            location = "Remote"

            job = make_job("arc", jid, title, company, location, url, keyword, "Arc")
            if job:
                jobs.append(job)

        except Exception as e:
            print(f"  [WARN] Arc parse error: {e}")

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
        print(f"  {keyword}: {len(jobs)} job(s) [Arc]")

        for job in jobs:
            if on_new_job:
                on_new_job(job)
            else:
                all_jobs.append(job)

        delay(1.0, 2.0)

    return all_jobs
