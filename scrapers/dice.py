"""
Dice scraper — https://www.dice.com
US-focused tech job board with global listings.
Has a public JSON search API.
"""

import re

from scrapers.base import delay, fetch_json, get_session, make_job


def _search_jobs(keyword, session):
    """Use Dice's public search API."""
    url = "https://job-search-api.svc.dhigroupinc.com/v1/dice/jobs/search"
    params = {
        "q": keyword,
        "countryCode2": "IN",
        "radius": "50",
        "radiusUnit": "mi",
        "page": "1",
        "pageSize": "20",
        "facets": "employmentType|postedDate|workFromHomeAvailability",
        "fields": "id|jobId|guid|summary|title|postedDate|modifiedDate|jobLocation.displayName|"
                  "detailsPageUrl|salary|clientBrandId|companyPageUrl|companyLogoUrl|"
                  "companyLogoUrlOptimized|positionId|companyName|employmentType|"
                  "isHighlighted|score|easyApply|employerType|workFromHomeAvailability|"
                  "isRemote|debug",
        "culture": "en",
        "recommendations": "true",
        "interactionId": "0",
        "fj": "true",
        "includeRemote": "true",
        "locationPrecision": "City",
    }

    data = fetch_json(url, session=session, params=params)
    if not data or "data" not in data:
        return []

    jobs = []
    for item in data.get("data", []):
        try:
            title = item.get("title", "Unknown Title")
            company = item.get("companyName", "Unknown Company")
            jid = item.get("id") or item.get("jobId") or item.get("guid", "")
            if not jid:
                continue

            details_url = item.get("detailsPageUrl", "")
            url = f"https://www.dice.com{details_url}" if details_url.startswith("/") else details_url
            if not url:
                url = f"https://www.dice.com/job-detail/{jid}"

            loc = item.get("jobLocation", {})
            if isinstance(loc, dict):
                location = loc.get("displayName", "Remote")
            elif isinstance(loc, list) and loc:
                location = loc[0].get("displayName", "Remote") if isinstance(loc[0], dict) else str(loc[0])
            else:
                location = "Remote"

            job = make_job("dice", str(jid), title, company, location, url, keyword, "Dice")
            if job:
                jobs.append(job)

        except Exception as e:
            print(f"  [WARN] Dice parse error: {e}")

    return jobs


def scrape_all_keywords(keywords, on_new_job=None):
    all_jobs = []
    session = get_session()

    for keyword in keywords:
        jobs = _search_jobs(keyword, session)
        print(f"  {keyword}: {len(jobs)} job(s) [Dice]")

        for job in jobs:
            if on_new_job:
                on_new_job(job)
            else:
                all_jobs.append(job)

        delay(1.5, 3.0)

    return all_jobs
