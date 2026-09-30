"""
Indeed India scraper — https://www.indeed.co.in
Uses HTTP requests + BeautifulSoup (no Selenium needed).
"""

import hashlib
import re

from scrapers.base import delay, fetch_soup, get_session, make_job, safe_text


def _build_urls(keyword, start=0):
    q = keyword.replace(" ", "+")
    return [
        f"https://www.indeed.co.in/jobs?q={q}&l=Bengaluru%2C+Karnataka&fromage=1&start={start}",
        f"https://www.indeed.co.in/jobs?q={q}&l=Remote&fromage=1&start={start}",
    ]


def _parse_jobs(soup, keyword):
    jobs = []
    cards = soup.select("div.job_seen_beacon")
    if not cards:
        cards = soup.select("div.resultContent")
    if not cards:
        cards = soup.select("td.resultContent")
    if not cards:
        # Fallback: look for any a tags with job links
        cards = soup.select("div[data-jk]")

    for card in cards:
        try:
            # Job ID
            jk = card.get("data-jk") or ""
            if not jk:
                parent = card.find_parent(attrs={"data-jk": True})
                jk = parent.get("data-jk", "") if parent else ""
            if not jk:
                link = card.find("a", href=re.compile(r"jk="))
                if link:
                    m = re.search(r"jk=([a-f0-9]+)", link.get("href", ""))
                    jk = m.group(1) if m else ""
            if not jk:
                # Generate from title+company
                title_text = safe_text(card.find("h2"))
                jk = hashlib.md5(title_text.encode()).hexdigest()[:12]

            # Title
            title_el = (
                card.select_one("h2.jobTitle a span")
                or card.select_one("h2.jobTitle span")
                or card.select_one("h2.jobTitle a")
                or card.select_one("h2.jobTitle")
                or card.find("a", attrs={"data-jk": True})
            )
            title = safe_text(title_el, "Unknown Title")

            # URL
            link_el = card.select_one("h2.jobTitle a") or card.find("a", href=re.compile(r"/rc/clk|/viewjob"))
            url = ""
            if link_el:
                href = link_el.get("href", "")
                if href.startswith("/"):
                    url = f"https://www.indeed.co.in{href}"
                elif href.startswith("http"):
                    url = href
                else:
                    url = f"https://www.indeed.co.in/viewjob?jk={jk}"
            else:
                url = f"https://www.indeed.co.in/viewjob?jk={jk}"

            # Company
            comp_el = (
                card.select_one("span[data-testid='company-name']")
                or card.select_one("span.companyName")
                or card.select_one("span.company")
            )
            company = safe_text(comp_el, "Unknown Company")

            # Location
            loc_el = (
                card.select_one("div[data-testid='text-location']")
                or card.select_one("div.companyLocation")
            )
            location = safe_text(loc_el, "Remote" if is_remote else "Bengaluru")
            if is_remote and "remote" not in location.lower() and "wfh" not in location.lower():
                location = f"{location} (Remote)"

            job = make_job("ind", jk, title, company, location, url, keyword, "Indeed")
            if job:
                jobs.append(job)

        except Exception as e:
            print(f"  [WARN] Indeed parse error: {e}")

    return jobs


def scrape_all_keywords(keywords, on_new_job=None):
    all_jobs = []
    seen_ids = set()
    session = get_session()

    for keyword in keywords:
        kw_jobs = []
        for url in _build_urls(keyword):
            is_remote = "l=Remote" in url
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

        print(f"  {keyword}: {len(kw_jobs)} job(s) [Indeed] (Bengaluru + Remote)")

    return all_jobs
