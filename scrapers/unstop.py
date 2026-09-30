"""
Unstop scraper — https://unstop.com
Popular Indian platform for jobs, internships, and competitions.
Has a public search API.
"""

import hashlib
import re

from scrapers.base import delay, fetch_json, fetch_soup, get_session, make_job, safe_text


def _search_api(keyword, session, extra_params=None, is_remote=False):
    """Try Unstop's public search API first."""
    url = "https://unstop.com/api/public/opportunity/search/new"
    params = {
        "opportunity": "jobs",
        "per_page": "20",
        "oppstatus": "open",
        "quickSearch": keyword,
    }
    if extra_params:
        params.update(extra_params)
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

            is_job_remote = (
                is_remote
                or item.get("job_type") == "work_from_home"
                or item.get("work_type") == "remote"
                or bool(item.get("is_work_from_home"))
                or "remote" in str(item.get("filters", "")).lower()
            )

            if is_job_remote:
                location = f"{city} (Remote)" if city else "Remote"
            else:
                location = city or "Bangalore"

            job = make_job("us", jid, title, company, location, url, keyword, "Unstop")
            if job:
                jobs.append(job)

        except Exception as e:
            print(f"  [WARN] Unstop API parse error: {e}")

    return jobs


def _parse_html(soup, keyword, is_remote=False):
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
            location = safe_text(loc_el, "Remote" if is_remote else "Bangalore")
            if is_remote and "remote" not in location.lower() and "wfh" not in location.lower():
                location = f"{location} (Remote)"

            job = make_job("us", jid, title, company, location, url, keyword, "Unstop")
            if job:
                jobs.append(job)

        except Exception as e:
            print(f"  [WARN] Unstop HTML parse error: {e}")

    return jobs


def scrape_all_keywords(keywords, on_new_job=None):
    all_jobs = []
    session = get_session()

    search_targets = [
        ({"city": "Bangalore"}, "https://unstop.com/jobs?keyword={q}&city=Bangalore", "Bangalore", False),
        ({"work_from_home": "1"}, "https://unstop.com/jobs?keyword={q}&work_from_home=1", "Remote", True),
    ]

    for keyword in keywords:
        q = keyword.replace(" ", "+")
        for extra_params, html_tmpl, label, is_remote in search_targets:
            # Try API first, fall back to HTML
            jobs = _search_api(keyword, session, extra_params=extra_params, is_remote=is_remote)
            if jobs is None:
                url = html_tmpl.format(q=q)
                soup = fetch_soup(url, session=session)
                jobs = _parse_html(soup, keyword, is_remote=is_remote) if soup else []

            print(f"  {keyword} ({label}): {len(jobs)} job(s) [Unstop]")

            for job in jobs:
                if on_new_job:
                    on_new_job(job)
                else:
                    all_jobs.append(job)

            delay(1.5, 3.0)

    return all_jobs
