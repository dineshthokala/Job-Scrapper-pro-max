"""
ZipRecruiter scraper — https://www.ziprecruiter.com
US-centric but has global listings. Public search pages.
"""

import hashlib
import re

from scrapers.base import delay, fetch_soup, get_session, make_job, safe_text


def _build_urls(keyword):
    q = keyword.replace(" ", "+")
    return [
        (f"https://www.ziprecruiter.com/jobs-search?search={q}&location=Bangalore%2C+India&days=1", False),
        (f"https://www.ziprecruiter.com/jobs-search?search={q}&location=Remote&days=1", True),
    ]


def _parse_jobs(soup, keyword, is_remote=False):
    jobs = []

    cards = (
        soup.select("article.job_result")
        or soup.select("div.job_result_two_pane")
        or soup.select("div[class*='JobCard']")
        or soup.select("article[data-job-id]")
    )

    for card in cards:
        try:
            jid = card.get("data-job-id", "")

            link = (
                card.select_one("h2 a")
                or card.find("a", class_=re.compile(r"job_link|jobTitle"))
                or card.find("a", href=re.compile(r"/jobs/|/c/"))
            )
            if not link:
                continue

            title = safe_text(link, "Unknown Title")
            href = link.get("href", "")
            url = href if href.startswith("http") else f"https://www.ziprecruiter.com{href}"

            if not jid:
                m = re.search(r"/([a-f0-9]{20,})", href)
                jid = m.group(1)[:16] if m else hashlib.md5(href.encode()).hexdigest()[:12]

            comp_el = (
                card.find("a", class_=re.compile(r"company_name"))
                or card.find("span", class_=re.compile(r"company"))
                or card.find("p", class_=re.compile(r"company"))
            )
            company = safe_text(comp_el, "Unknown Company")

            loc_el = card.find("span", class_=re.compile(r"location"))
            location = safe_text(loc_el, "Remote" if is_remote else "Bangalore")
            if is_remote and "remote" not in location.lower() and "wfh" not in location.lower():
                location = f"{location} (Remote)"

            job = make_job("zr", str(jid), title, company, location, url, keyword, "ZipRecruiter")
            if job:
                jobs.append(job)

        except Exception as e:
            print(f"  [WARN] ZipRecruiter parse error: {e}")

    return jobs


def scrape_all_keywords(keywords, on_new_job=None):
    all_jobs = []
    session = get_session()

    for keyword in keywords:
        for url, is_remote in _build_urls(keyword):
            soup = fetch_soup(url, session=session)
            if not soup:
                continue

            jobs = _parse_jobs(soup, keyword, is_remote=is_remote)
            loc_label = "Remote" if is_remote else "Bangalore"
            print(f"  {keyword} ({loc_label}): {len(jobs)} job(s) [ZipRecruiter]")

            for job in jobs:
                if on_new_job:
                    on_new_job(job)
                else:
                    all_jobs.append(job)

            delay(2.0, 4.0)

    return all_jobs
