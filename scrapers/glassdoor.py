"""
Glassdoor scraper — https://www.glassdoor.co.in
Uses HTTP + BeautifulSoup. Glassdoor has aggressive anti-bot but
initial search pages often work with proper headers.
"""

import hashlib
import re

from scrapers.base import delay, fetch_soup, get_session, make_job, safe_text


def _build_url(keyword):
    slug = keyword.lower().replace(" ", "-")
    return f"https://www.glassdoor.co.in/Job/bangalore-{slug}-jobs-SRCH_IL.0,9_IC2940587_KO10,{10 + len(slug)}.htm"


def _parse_jobs(soup, keyword):
    jobs = []

    cards = (
        soup.select("li.JobsList_jobListItem__")
        or soup.select("li[data-test='jobListing']")
        or soup.select("ul.JobsList_jobsList__ li")
        or soup.select("div.JobCard_jobCardContainer__")
    )

    for card in cards:
        try:
            # Title + link
            link = (
                card.find("a", attrs={"data-test": "job-title"})
                or card.select_one("a.JobCard_jobTitle__")
                or card.find("a", href=re.compile(r"/partner/jobListing|/job-listing/"))
            )
            if not link:
                continue

            title = safe_text(link, "Unknown Title")
            href = link.get("href", "")
            url = f"https://www.glassdoor.co.in{href}" if href.startswith("/") else href

            m = re.search(r"jobListingId=(\d+)|/(\d+)\.htm", href)
            jid = m.group(1) or m.group(2) if m else hashlib.md5(href.encode()).hexdigest()[:12]

            # Company
            comp_el = (
                card.find("span", class_=re.compile(r"EmployerProfile_compactEmployerName__"))
                or card.find("div", attrs={"data-test": "emp-name"})
                or card.find("span", class_=re.compile(r"companyName"))
            )
            company = safe_text(comp_el, "Unknown Company")

            # Location
            loc_el = (
                card.find("div", attrs={"data-test": "emp-location"})
                or card.find("span", class_=re.compile(r"location"))
            )
            location = safe_text(loc_el, "Bangalore")

            job = make_job("gd", jid, title, company, location, url, keyword, "Glassdoor")
            if job:
                jobs.append(job)

        except Exception as e:
            print(f"  [WARN] Glassdoor parse error: {e}")

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
        print(f"  {keyword}: {len(jobs)} job(s) [Glassdoor]")

        for job in jobs:
            if on_new_job:
                on_new_job(job)
            else:
                all_jobs.append(job)

        delay(3.0, 5.0)

    return all_jobs
