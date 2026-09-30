"""
Hirist scraper — https://www.hirist.tech
Premium tech job portal in India (powered by SeleniumBase).
"""

import re
import time
from bs4 import BeautifulSoup

from driver import get_driver, passes_filters


def _scrape_keyword(keyword, driver, on_new_job=None):
    slug = keyword.lower().strip().replace(" ", "-")
    url = f"https://www.hirist.tech/k/{slug}-jobs.html"
    
    try:
        driver.get(url)
        time.sleep(4)
    except Exception as e:
        print(f"  [WARN] Failed to load {url}: {e}")
        return []

    soup = BeautifulSoup(driver.page_source, "lxml")
    jobs = []
    seen_ids = set()

    for a in soup.find_all("a", href=re.compile(r"/j/([a-zA-Z0-9_\-]+-(\d+))")):
        try:
            href = a.get("href", "")
            m = re.search(r"-(\d+)(?:\?|$)", href)
            jid = m.group(1) if m else None
            if not jid or jid in seen_ids:
                continue

            parent = a.find_parent(lambda p: len(p.find_all(string=True)) > 5)
            if not parent:
                continue

            strings = list(parent.stripped_strings)
            if not strings:
                continue

            raw_title = strings[0]
            if " - " in raw_title:
                parts = raw_title.split(" - ", 1)
                company = parts[0].strip()
                title = parts[1].strip()
            else:
                company = "Hirist Recruiter"
                title = raw_title

            location = ""
            exp_text = None
            if len(strings) > 1 and "yr" in strings[1].lower():
                exp_text = strings[1]

            # Look through strings for explicit location
            for s in strings[1:]:
                s_lower = s.lower()
                if any(w in s_lower for w in ["bangalore", "bengaluru", "blr", "remote", "wfh", "work from home", "pune", "hyderabad", "mumbai", "noida", "gurgaon", "chennai"]):
                    location = s
                    break
            if not location:
                if len(strings) > 2 and exp_text:
                    location = strings[2]
                else:
                    location = "Bengaluru / Remote"

            clean_href = href.split("?")[0]
            job_url = f"https://www.hirist.tech{clean_href}"

            passes, reason = passes_filters(title, company, card_text=exp_text, location=location)
            if not passes:
                continue

            job = {
                "job_id": f"ht_{jid}",
                "title": title,
                "company": company,
                "location": location,
                "url": job_url,
                "keyword": keyword,
                "source": "Hirist",
            }

            seen_ids.add(jid)
            jobs.append(job)
            if on_new_job:
                on_new_job(job)

        except Exception as ex:
            print(f"  [WARN] Hirist card parse error: {ex}")

    return jobs


def scrape_all_keywords(keywords, on_new_job=None):
    driver = get_driver()
    all_jobs = []

    for keyword in keywords:
        jobs = _scrape_keyword(keyword, driver, on_new_job)
        print(f"  {keyword}: {len(jobs)} job(s) [Hirist]")
        all_jobs.extend(jobs)
        time.sleep(2)

    return all_jobs
