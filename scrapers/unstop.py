"""
Unstop scraper — https://unstop.com
Popular Indian platform for jobs, internships, and competitions.
Has a public search API.
"""

import hashlib
import re

from scrapers.base import delay, fetch_json, fetch_soup, get_session, make_job, safe_text


def _search_api(keyword, session):
    """Try Unstop's public search API first."""
    url = "https://unstop.com/api/public/opportunity/search/new"
    params = {
        "opportunity": "jobs",
        "per_page": "20",
        "oppstatus": "open",
        "quickSearch": keyword,
        "city": "Bangalore",
    }
    data = fetch_json(url, session=session, params=params)
    if not data:
        return None  # signal to fall back to HTML

    jobs = []
    results = data.get("data", {}).get("data", [])
    if not results and isinstance(data.get("data"), list):
        results = data["data"]

    for item in results:
        try:
            title = item.get("title", "Unknown Title")
            company = item.get("organisation", {}).get("name", "Unknown Company") if isinstance(item.get("organisation"), dict) else "Unknown Company"
            jid = str(item.get("id", ""))
            if not jid:
                continue

            slug = item.get("public_url", "") or item.get("seo_url", "")
            url = f"https://unstop.com{slug}" if slug.startswith("/") else f"https://unstop.com/jobs/{slug}" if slug else f"https://unstop.com/job/{jid}"

            city = ""
            if isinstance(item.get("city"), list) and item["city"]:
                city = item["city"][0] if isinstance(item["city"][0], str) else item["city"][0].get("name", "")
            elif isinstance(item.get("city"), str):
                city = item["city"]
            location = city or "India"

            job = make_job("us", jid, title, company, location, url, keyword, "Unstop")
            if job:
                jobs.append(job)

        except Exception as e:
            print(f"  [WARN] Unstop API parse error: {e}")

    return jobs


def _parse_html(soup, keyword):
    """Fallback HTML parser."""
    jobs = []
    cards = (
        soup.select("div.single_opportunity")
        or soup.select("div[class*='opportunity-card']")
        or soup.select("a[href*='/jobs/']")
    )

    for card in cards:
        try:
            if card.name == "a":
                link = card
            else:
                link = card.find("a", href=re.compile(r"/jobs?/"))
            if not link:
                continue

            href = link.get("href", "")
            title = safe_text(link.find("h3") or link.find("h2") or link, "Unknown Title")
            url = f"https://unstop.com{href}" if href.startswith("/") else href

            m = re.search(r"/(\d+)/?$", href)
            jid = m.group(1) if m else hashlib.md5(href.encode()).hexdigest()[:12]

            comp_el = card.find("span", class_=re.compile(r"org|company"))
            company = safe_text(comp_el, "Unknown Company")

            loc_el = card.find("span", class_=re.compile(r"location|city"))
            location = safe_text(loc_el, "India")

            job = make_job("us", jid, title, company, location, url, keyword, "Unstop")
            if job:
                jobs.append(job)

        except Exception as e:
            print(f"  [WARN] Unstop HTML parse error: {e}")

    return jobs


def scrape_all_keywords(keywords, on_new_job=None):
    all_jobs = []
    session = get_session()

    for keyword in keywords:
        # Try API first, fall back to HTML
        jobs = _search_api(keyword, session)
        if jobs is None:
            url = f"https://unstop.com/jobs?keyword={keyword.replace(' ', '+')}&city=Bangalore"
            soup = fetch_soup(url, session=session)
            jobs = _parse_html(soup, keyword) if soup else []

        print(f"  {keyword}: {len(jobs)} job(s) [Unstop]")

        for job in jobs:
            if on_new_job:
                on_new_job(job)
            else:
                all_jobs.append(job)

        delay(1.5, 3.0)

    return all_jobs
