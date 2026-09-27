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
}


def _post_embed(embed: dict) -> bool:
    """POST a single embed to Discord, handling 429 rate-limit with one retry."""
    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]}, timeout=10)
        if resp.status_code == 429:
            delay = resp.json().get("retry_after", 5) if resp.text else 5
            time.sleep(delay)
            resp = requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]}, timeout=10)
        return resp.status_code in (200, 204)
    except requests.RequestException as e:
        print(f"  [ERROR] Discord POST failed: {e}")
        return False


def send_discord_notification(job):
    """Send a rich embed to Discord for a single job posting."""
    source = job.get("source", "Unknown")
    color = SOURCE_COLORS.get(source, 0x808080)

    embed = {
        "title": job["title"],
        "url": job["url"],
        "color": color,
        "fields": [
            {"name": "Company", "value": job["company"], "inline": True},
            {"name": "Location", "value": job["location"], "inline": True},
            {"name": "Source", "value": source, "inline": True},
            {"name": "Keyword", "value": job["keyword"], "inline": True},
            {"name": "Apply", "value": f"[View Job]({job['url']})"},
        ],
        "footer": {"text": f"Job ID: {job['job_id']}"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return _post_embed(embed)
 
 
def send_google_sheet_row(job) -> bool:
    """Send newly found job to Google Sheet via Google Apps Script Webhook."""
    if not GOOGLE_SHEET_WEBHOOK_URL:
        return False
    try:
        payload = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "location": job.get("location", ""),
            "source": job.get("source", ""),
            "keyword": job.get("keyword", ""),
            "url": job.get("url", ""),
            "job_id": job.get("job_id", ""),
            "status": "New",
        }
        resp = requests.post(GOOGLE_SHEET_WEBHOOK_URL, json=payload, timeout=10)
        return resp.status_code in (200, 201, 302)
    except Exception as e:
        print(f"  [ERROR] Google Sheet sync failed: {e}")
        return False

