"""
Foundit (formerly Monster India) scraper — https://www.foundit.in
Scrapes real-time jobs in Bangalore using SeleniumBase headless browser.
"""

import time
import urllib.parse
from bs4 import BeautifulSoup

from driver import get_driver, passes_filters


def _scrape_keyword(keyword, driver, on_new_job=None):
    encoded_kw = urllib.parse.quote(keyword)
    urls = [
        (f"https://www.foundit.in/srp/results?query={encoded_kw}&locations=bangalore", False),
        (f"https://www.foundit.in/srp/results?query={encoded_kw}&locations=remote", True),
    ]
    jobs = []
    seen_ids = set()

    for url, is_remote in urls:
        try:
            driver.get(url)
            time.sleep(3)
        except Exception as e:
            print(f"  [WARN] Failed to load Foundit {url}: {e}")
            continue

        soup = BeautifulSoup(driver.page_source, "lxml")
        cards = soup.select("div.cardContainer")
        for card in cards:
            try:
                jid = card.get("id", "").strip()
                if not jid or jid in seen_ids:
                    continue

                # Title
                title_el = (
                    card.select_one(".cardTitle")
                    or card.select_one(".headerContent a")
                    or card.select_one(".headerContent")
                    or card.select_one("h3")
                    or card.select_one("h2")
                )
                title = title_el.get_text(strip=True) if title_el else "Flutter Developer"

                # Company
                comp_el = (
                    card.select_one(".companyName")
                    or card.select_one(".company")
                    or card.select_one("a[class*='company']")
                )
                company = comp_el.get_text(strip=True) if comp_el else "Foundit Employer"

                # Location & experience
                loc_el = card.select_one(".location, [class*='location']")
                location = loc_el.get_text(strip=True) if loc_el else ("Remote" if is_remote else "Bengaluru")
                if is_remote and "remote" not in location.lower() and "wfh" not in location.lower():
                    location = f"{location} (Remote)"

                exp_el = card.select_one(".experience, [class*='experience'], [class*='exp']")
                card_text = exp_el.get_text(strip=True) if exp_el else None

                job_url = f"https://www.foundit.in/seeker/job-details?id={jid}"

                passes, reason = passes_filters(title, company, card_text=card_text, location=location)
                if not passes:
                    continue

                job = {
                    "job_id": f"fi_{jid}",
                    "title": title,
                    "company": company,
                    "location": location,
                    "url": job_url,
                    "keyword": keyword,
                    "source": "Foundit",
                }

                seen_ids.add(jid)
                jobs.append(job)
                if on_new_job:
                    on_new_job(job)

            except Exception as ex:
                print(f"  [WARN] Foundit card parse error: {ex}")

    return jobs


def scrape_all_keywords(keywords, on_new_job=None):
    driver = get_driver()
    all_jobs = []

    for keyword in keywords:
        jobs = _scrape_keyword(keyword, driver, on_new_job)
        print(f"  {keyword}: {len(jobs)} job(s) [Foundit]")
        all_jobs.extend(jobs)
        time.sleep(2)

    return all_jobs
