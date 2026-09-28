"""
WeWorkRemotely scraper — https://weworkremotely.com
Scrapes remote programming jobs via WeWorkRemotely's public RSS feeds.
"""

import hashlib
import xml.etree.ElementTree as ET
import requests

from scrapers.base import delay, make_job

RSS_FEEDS = [
    "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
]


def scrape_all_keywords(keywords, on_new_job=None):
    all_jobs = []
    seen_urls = set()

    for feed_url in RSS_FEEDS:
        try:
            resp = requests.get(feed_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            if resp.status_code != 200:
                continue

            root = ET.fromstring(resp.content)
            channel = root.find("channel")
            if channel is None:
                continue

            items = channel.findall("item")
            for item in items:
                try:
                    raw_title = item.find("title").text if item.find("title") is not None else ""
                    link = item.find("link").text if item.find("link") is not None else ""
                    if not link or link in seen_urls:
                        continue

                    if ":" in raw_title:
                        company, title = raw_title.split(":", 1)
                        company = company.strip()
                        title = title.strip()
                    else:
                        company = "Remote Company"
                        title = raw_title.strip()

                    jid = hashlib.md5(link.encode()).hexdigest()[:12]
                    location = "Remote"

                    # Check against each keyword
                    for kw in keywords:
                        job = make_job("wwr", jid, title, company, location, link, kw, "WeWorkRemotely")
                        if job:
                            seen_urls.add(link)
                            if on_new_job:
                                on_new_job(job)
                            else:
                                all_jobs.append(job)
                            break

                except Exception as ex:
                    print(f"  [WARN] WWR item parse error: {ex}")

        except Exception as e:
            print(f"  [WARN] WWR feed fetch failed: {e}")

        delay(1.0, 2.0)

    print(f"  WeWorkRemotely: {len(all_jobs)} candidate(s)")
    return all_jobs
