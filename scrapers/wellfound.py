"""
Wellfound (AngelList Talent) scraper — https://wellfound.com
Startup jobs platform with public listings.
"""

import hashlib
import re

from scrapers.base import delay, fetch_soup, get_session, make_job, safe_text


def _build_url(keyword):
    slug = keyword.lower().replace(" ", "-")
    return f"https://wellfound.com/role/l/{slug}/india"


def _parse_jobs(soup, keyword):
    jobs = []

    # Wellfound renders job cards in various formats
    cards = (
        soup.select("div[data-test='StartupResult']")
        or soup.select("div.styles_result__")
        or soup.select("div[class*='StartupResult']")
        or soup.select("div.mb-6")
    )

    for card in cards:
        try:
            # Company name
            comp_el = (
                card.select_one("h2 a")
                or card.select_one("a[class*='company']")
                or card.find("a", href=re.compile(r"/company/"))
            )
            company = safe_text(comp_el, "")
            if not company:
                continue

            # Job listings within this company card
            job_links = card.select("a[href*='/jobs/']") or card.find_all("a", href=re.compile(r"/jobs/"))

            for link in job_links:
                href = link.get("href", "")
                title = safe_text(link)
                if not title or len(title) < 3:
                    continue

                url = f"https://wellfound.com{href}" if href.startswith("/") else href

                m = re.search(r"/jobs/(\d+)", href)
                jid = m.group(1) if m else hashlib.md5((company + title).encode()).hexdigest()[:12]

                # Location — try to find in surrounding context
                loc_el = card.find("span", string=re.compile(r"Bangalore|Bengaluru|Remote|India", re.I))
                location = safe_text(loc_el, "India")

                job = make_job("wf", jid, title, company, location, url, keyword, "Wellfound")
                if job:
                    jobs.append(job)

        except Exception as e:
            print(f"  [WARN] Wellfound parse error: {e}")

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
        print(f"  {keyword}: {len(jobs)} job(s) [Wellfound]")

        for job in jobs:
            if on_new_job:
                on_new_job(job)
            else:
                all_jobs.append(job)

        delay(2.0, 4.0)

    return all_jobs
