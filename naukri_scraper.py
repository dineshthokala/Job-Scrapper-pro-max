import time

from bs4 import BeautifulSoup

from driver import enforce_tab_limit, get_driver, passes_filters


def _build_search_urls(keyword):
    slug = keyword.lower().replace(" ", "-")
    return [
        f"https://www.naukri.com/{slug}-jobs-in-bengaluru?experience=0&jobAge=1",
        f"https://www.naukri.com/remote-{slug}-jobs?experience=0&jobAge=1",
    ]


def _parse_job_cards(soup, keyword, is_remote=False):
    jobs = []
    job_cards = soup.find_all("div", class_="srp-jobtuple-wrapper")
    if not job_cards:
        job_cards = soup.find_all(attrs={"data-job-id": True})

    for card in job_cards:
        try:
            job_id = card.get("data-job-id")
            if not job_id:
                continue

            title_el = card.find("a", class_="title")
            title = title_el.get_text(strip=True) if title_el else "Unknown Title"
            job_url = title_el.get("href", "") if title_el else ""

            comp_el = card.find("a", class_="comp-name")
            company = comp_el.get_text(strip=True) if comp_el else "Unknown Company"

            loc_el = card.find("span", class_="locWdth")
            location = loc_el.get_text(strip=True) if loc_el else ("Remote" if is_remote else "Bengaluru")
            if is_remote and "remote" not in location.lower() and "wfh" not in location.lower():
                location = f"{location} (Remote)"

            time_el = card.find("span", class_="job-post-day")
            card_text = time_el.get_text(strip=True) if time_el else ""

            passes, reason = passes_filters(title, company, card_text, location)
            if not passes:
                print(f"    [SKIP] {reason}")
                continue

            if not job_url.startswith("http"):
                job_url = f"https://www.naukri.com{job_url}"

            jobs.append({
                "job_id": f"nk_{job_id}",
                "title": title,
                "company": company,
                "location": location,
                "url": job_url,
                "keyword": keyword,
                "source": "Naukri",
            })
        except Exception as e:
            print(f"  [WARN] Naukri parse error: {e}")

    return jobs


def scrape_all_keywords(keywords, on_new_job=None):
    all_jobs = []
    seen_ids = set()
    driver = get_driver()

    for keyword in keywords:
        urls = _build_search_urls(keyword)
        kw_jobs = []

        for url in urls:
            is_remote = "remote-" in url
            try:
                driver.get(url)
                time.sleep(2)
                for _ in range(3):
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(0.4)

                soup = BeautifulSoup(driver.page_source, "lxml")
                found = _parse_job_cards(soup, keyword, is_remote=is_remote)
                for j in found:
                    if j["job_id"] not in seen_ids:
                        seen_ids.add(j["job_id"])
                        kw_jobs.append(j)
                        if on_new_job:
                            on_new_job(j)
                        else:
                            all_jobs.append(j)
            except Exception as e:
                print(f"  [ERROR] Naukri '{keyword}' at {url}: {e}")

        print(f"  [Naukri] {keyword}: {len(kw_jobs)} job(s) (Bengaluru + Remote)")
        enforce_tab_limit(2)

    return all_jobs