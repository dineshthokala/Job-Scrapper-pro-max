"""Discord webhook notifications for new job postings."""

import time
from datetime import datetime, timezone

import requests

from config import DISCORD_WEBHOOK_URL, GOOGLE_SHEET_WEBHOOK_URL

SOURCE_COLORS = {
    "LinkedIn":     0x0A66C2,
    "Naukri":       0x2D69F0,
    "Internshala":  0x00A5EC,
    "Indeed":       0x003A9B,
    "Glassdoor":    0x0CAA41,
    "Wellfound":    0x000000,
    "YCombinator":  0xF26522,
    "Instahyre":    0x5D3FD3,
    "Cutshort":     0x6C63FF,
    "Dice":         0xEB1C26,
    "CareerJet":    0x1A73E8,
    "ZipRecruiter": 0x25C764,
    "HiringCafe":   0xF59E0B,
    "Otta":         0x171717,
    "Peerlist":     0x00AA45,
    "Arc":          0x6E56CF,
    "Unstop":       0x1E88E5,
    "AccioJobs":    0x4F46E5,
    "OneRoadmap":   0x6366F1,
    "Hirist":       0xFF5722,
    "WeWorkRemotely": 0xEE3124,
    "jobs.a16z":    0x1E293B,
    "Foundit":      0x7C3AED,
}



def _post_embed(embed: dict) -> bool:
    """POST a single embed to Discord, handling 429 rate-limit with one retry."""
    url = (DISCORD_WEBHOOK_URL or "").strip().strip("\"'")
    if not url:
        print("  [WARN] DISCORD_WEBHOOK_URL is not set.")
        return False
    try:
        resp = requests.post(url, json={"embeds": [embed]}, timeout=15)
        if resp.status_code == 429:
            delay = resp.json().get("retry_after", 5) if resp.text else 5
            time.sleep(delay)
            resp = requests.post(url, json={"embeds": [embed]}, timeout=15)
        if resp.status_code not in (200, 204):
            print(f"  [ERROR] Discord webhook returned HTTP {resp.status_code}: {resp.text[:200]}")
            return False
        return True
    except requests.RequestException as e:
        print(f"  [ERROR] Discord POST failed: {e}")
        return False


def send_discord_notification(job):
    """Send a rich embed to Discord for a single job posting."""
    source = str(job.get("source") or "Unknown").strip()
    color = SOURCE_COLORS.get(source, 0x808080)

    title = str(job.get("title") or "Flutter Role").strip()
    company = str(job.get("company") or "Company").strip()
    location = str(job.get("location") or "Bengaluru / Remote").strip() or "Bengaluru / Remote"
    keyword = str(job.get("keyword") or "Flutter").strip() or "Flutter"
    job_url = str(job.get("url") or "").strip()
    if not job_url.startswith("http"):
        job_url = "https://www.linkedin.com"

    embed = {
        "title": title,
        "url": job_url,
        "color": color,
        "fields": [
            {"name": "Company", "value": company, "inline": True},
            {"name": "Location", "value": location, "inline": True},
            {"name": "Source", "value": source, "inline": True},
            {"name": "Keyword", "value": keyword, "inline": True},
            {"name": "Apply", "value": f"[View Job]({job_url})"},
        ],
        "footer": {"text": f"Job ID: {job.get('job_id', '')}"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return _post_embed(embed)


def send_google_sheet_row(job) -> bool:
    """Send newly found job to Google Sheet via Google Apps Script Webhook."""
    url = (GOOGLE_SHEET_WEBHOOK_URL or "").strip().strip("\"'")
    if not url:
        return False
    try:
        payload = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "title": str(job.get("title") or ""),
            "company": str(job.get("company") or ""),
            "location": str(job.get("location") or "Bengaluru / Remote"),
            "source": str(job.get("source") or ""),
            "keyword": str(job.get("keyword") or "Flutter"),
            "url": str(job.get("url") or ""),
            "job_id": str(job.get("job_id") or ""),
            "status": "New",
        }
        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=15)
        if resp.status_code not in (200, 201, 302):
            print(f"  [ERROR] Google Sheet returned HTTP {resp.status_code}: {resp.text[:200]}")
            return False
        return True
    except Exception as e:
        print(f"  [ERROR] Google Sheet sync exception: {e}")
        return False


