"""
main.py — parallel scraping with instant per-job Discord notifications
and SQLite persistence for the web dashboard.

Thread 1: LinkedIn  (Selenium-based, slow)
Thread 2: Internshala → Naukri  (Selenium-based)
Thread 3: All HTTP-based scrapers (fast, no browser needed)

Jobs are saved to the database and sent to Discord the moment they are
found and verified as new.
"""

import collections
import signal
import sys
import threading
from datetime import datetime

from config import (
    DISCORD_WEBHOOK_URL,
    ENABLE_ACCIOJOBS,
    ENABLE_ARC,
    ENABLE_CAREERJET,
    ENABLE_CUTSHORT,
    ENABLE_DICE,
    ENABLE_GLASSDOOR,
    ENABLE_HIRINGCAFE,
    ENABLE_INDEED,
    ENABLE_INSTAHYRE,
    ENABLE_INTERNSHALA,
    ENABLE_LINKEDIN,
    ENABLE_NAUKRI,
    ENABLE_OTTA,
    ENABLE_PEERLIST,
    ENABLE_UNSTOP,
    ENABLE_WELLFOUND,
    ENABLE_YCOMBINATOR,
    ENABLE_ZIPRECRUITER,
    ENABLE_ONEROADMAP,
    ENABLE_HIRIST,
    ENABLE_WEWORKREMOTELY,
    ENABLE_A16Z,
    ENABLE_FOUNDIT,
    RUN_INTERVAL,
    SEARCH_KEYWORDS,
)


_shutdown = threading.Event()

# ── Thread-safe log buffer (consumed by the dashboard SSE endpoint) ────

_log_buffer = collections.deque(maxlen=500)
_log_lock = threading.Lock()
_log_subscribers = []          # list of threading.Event objects


def _log(msg: str):
    """Print a message AND store it in the ring buffer for the dashboard."""
    print(msg)
    ts = datetime.now().strftime("%H:%M:%S")
    entry = f"[{ts}] {msg}"
    with _log_lock:
        _log_buffer.append(entry)
        for evt in _log_subscribers:
            evt.set()


def subscribe_logs():
    """Return (event, buffer_ref) for SSE streaming."""
    evt = threading.Event()
    with _log_lock:
        _log_subscribers.append(evt)
    return evt, _log_buffer


def unsubscribe_logs(evt):
    with _log_lock:
        if evt in _log_subscribers:
            _log_subscribers.remove(evt)


# ── Scraper status (exposed to the dashboard) ─────────────────────────

_scrape_status = {
    "state": "idle",            # idle | running | error
    "last_run": None,           # ISO timestamp
    "current_sources": [],
}
_status_lock = threading.Lock()


def get_scrape_status():
    with _status_lock:
        return dict(_scrape_status)


def _set_status(state, sources=None):
    with _status_lock:
        _scrape_status["state"] = state
        if sources is not None:
            _scrape_status["current_sources"] = sources
        if state == "idle":
            _scrape_status["last_run"] = datetime.now().isoformat()


# ── Signal handling ────────────────────────────────────────────────────

def _handle_sigint(sig, frame):
    _log("[INFO] Ctrl+C received — shutting down gracefully...")
    _shutdown.set()


signal.signal(signal.SIGINT, _handle_sigint)


# ── Job callback (DB + Discord) ───────────────────────────────────────

def _make_instant_notifier(label: str):
    """
    Returns a callback: on_new_job(job) → save to DB, notify Discord if new.
    Thread-safe.
    """
    from database import upsert_job
    from notifier import send_discord_notification, send_google_sheet_row
    from config import GOOGLE_SHEET_WEBHOOK_URL

    lock = threading.Lock()
    counter = {"found": 0, "new": 0}

    def on_new_job(job: dict):
        with lock:
            counter["found"] += 1
            is_new = upsert_job(job)
            if not is_new:
                return
            counter["new"] += 1
            _log(f"  [NEW] {job['title']} at {job['company']} [{label}]")
            if DISCORD_WEBHOOK_URL:
                if send_discord_notification(job):
                    _log(f"  [NOTIFY] Discord sent for {job['title']}")
                else:
                    _log(f"  [WARN] Discord notify failed for {job['job_id']}")
            if GOOGLE_SHEET_WEBHOOK_URL:
                if send_google_sheet_row(job):
                    _log(f"  [SHEETS] Google Sheet updated for {job['title']}")
                else:
                    _log(f"  [WARN] Google Sheet update failed for {job['job_id']}")


    def get_counts():
        with lock:
            return dict(counter)

    def reset_counts():
        with lock:
            counter["found"] = 0
            counter["new"] = 0

    on_new_job.get_counts = get_counts
    on_new_job.reset_counts = reset_counts
    return on_new_job


# ── Scraper runners ───────────────────────────────────────────────────

def _run_startup_sweep(li_notify):
    """One-time 24h LinkedIn sweep to catch jobs posted while offline."""
    if not ENABLE_LINKEDIN:
        return
    _log("--- [LinkedIn] Startup 24h sweep ---")
    try:
        from linkedin_scraper import startup_sweep
        startup_sweep(SEARCH_KEYWORDS, on_new_job=li_notify)
    except Exception as e:
        _log(f"[LinkedIn] Startup sweep ERROR: {e}")
        from driver import reset_driver
        reset_driver()


def _run_linkedin(notify):
    """Thread 1: LinkedIn (Selenium)."""
    if not ENABLE_LINKEDIN:
        return
    _log("--- [LinkedIn] ---")
    try:
        from linkedin_scraper import scrape_all_keywords
        scrape_all_keywords(SEARCH_KEYWORDS, on_new_job=notify)
    except Exception as e:
        _log(f"[LinkedIn] ERROR: {e}")
        from driver import reset_driver
        reset_driver()


def _run_selenium_group(notify):
    """Thread 2: Internshala → Naukri (Selenium)."""
    if ENABLE_INTERNSHALA:
        _log("--- [Internshala] ---")
        try:
            from internshala_scraper import scrape_all_keywords
            scrape_all_keywords(SEARCH_KEYWORDS, on_new_job=notify)
        except Exception as e:
            _log(f"[Internshala] ERROR: {e}")
            from driver import reset_driver
            reset_driver()

    if ENABLE_NAUKRI:
        _log("--- [Naukri] ---")
        try:
            from naukri_scraper import scrape_all_keywords
            scrape_all_keywords(SEARCH_KEYWORDS, on_new_job=notify)
        except Exception as e:
            _log(f"[Naukri] ERROR: {e}")
            from driver import reset_driver
            reset_driver()

    if ENABLE_HIRIST:
        _log("--- [Hirist] ---")
        try:
            from scrapers.hirist import scrape_all_keywords
            scrape_all_keywords(SEARCH_KEYWORDS, on_new_job=notify)
        except Exception as e:
            _log(f"[Hirist] ERROR: {e}")
            from driver import reset_driver
            reset_driver()

    if ENABLE_FOUNDIT:
        _log("--- [Foundit] ---")
        try:
            from scrapers.foundit import scrape_all_keywords
            scrape_all_keywords(SEARCH_KEYWORDS, on_new_job=notify)
        except Exception as e:
            _log(f"[Foundit] ERROR: {e}")
            from driver import reset_driver
            reset_driver()

    from driver import reset_driver
    reset_driver()


# Map of (config_flag, module_path, source_label) for all HTTP scrapers
_HTTP_SCRAPERS = [
    (ENABLE_INDEED,         "scrapers.indeed",         "Indeed"),
    (ENABLE_CAREERJET,      "scrapers.careerjet",      "CareerJet"),
    (ENABLE_ARC,            "scrapers.arc",            "Arc"),
    (ENABLE_YCOMBINATOR,    "scrapers.ycombinator",    "YCombinator"),
    (ENABLE_WELLFOUND,      "scrapers.wellfound",      "Wellfound"),
    (ENABLE_INSTAHYRE,      "scrapers.instahyre",      "Instahyre"),
    (ENABLE_GLASSDOOR,      "scrapers.glassdoor",      "Glassdoor"),
    (ENABLE_CUTSHORT,       "scrapers.cutshort",       "Cutshort"),
    (ENABLE_DICE,           "scrapers.dice",           "Dice"),
    (ENABLE_ZIPRECRUITER,   "scrapers.ziprecruiter",   "ZipRecruiter"),
    (ENABLE_HIRINGCAFE,     "scrapers.hiringcafe",     "HiringCafe"),
    (ENABLE_OTTA,           "scrapers.otta",           "Otta"),
    (ENABLE_PEERLIST,       "scrapers.peerlist",       "Peerlist"),
    (ENABLE_UNSTOP,         "scrapers.unstop",         "Unstop"),
    (ENABLE_ACCIOJOBS,      "scrapers.acciojobs",      "AccioJobs"),
    (ENABLE_ONEROADMAP,     "scrapers.oneroadmap",     "OneRoadmap"),
    (ENABLE_WEWORKREMOTELY, "scrapers.weworkremotely", "WeWorkRemotely"),
    (ENABLE_A16Z,           "scrapers.a16z",           "jobs.a16z"),
]


def _run_http_scrapers(notify):
    """Thread 3: All lightweight HTTP-based scrapers (no Selenium)."""
    import importlib

    for enabled, module_path, label in _HTTP_SCRAPERS:
        if not enabled:
            continue
        _log(f"--- [{label}] ---")
        try:
            mod = importlib.import_module(module_path)
            mod.scrape_all_keywords(SEARCH_KEYWORDS, on_new_job=notify)
        except Exception as e:
            _log(f"[{label}] ERROR: {e}")


# ── Public scrape cycle (called by both the loop and the API) ─────────

_scrape_lock = threading.Lock()


def run_scrape_cycle(sources=None):
    """
    Run a single scrape cycle. Thread-safe (only one cycle at a time).
    `sources` is an optional list like ["LinkedIn", "Naukri"] to limit.
    Returns a summary dict.
    """
    from database import finish_scrape_run, log_scrape_run

    if not _scrape_lock.acquire(blocking=False):
        _log("[WARN] Scrape already in progress — skipping.")
        return {"error": "already_running"}

    try:
        # Determine which sources to run
        all_sources = []
        if ENABLE_LINKEDIN:
            all_sources.append("LinkedIn")
        if ENABLE_INTERNSHALA:
            all_sources.append("Internshala")
        if ENABLE_NAUKRI:
            all_sources.append("Naukri")
        if ENABLE_HIRIST:
            all_sources.append("Hirist")
        if ENABLE_FOUNDIT:
            all_sources.append("Foundit")
        for enabled, _, label in _HTTP_SCRAPERS:
            if enabled:
                all_sources.append(label)

        active = sources if sources else all_sources

        _set_status("running", active)
        run_id = log_scrape_run(", ".join(active))

        li_notify = _make_instant_notifier("LinkedIn")
        sel_notify = _make_instant_notifier("Selenium")
        http_notify = _make_instant_notifier("HTTP")

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _log(f"{'=' * 55}")
        _log(f"[{now}] Scrape cycle — {len(active)} source(s)")
        _log(f"{'=' * 55}")

        threads = []

        # Thread 1: LinkedIn
        if "LinkedIn" in active:
            t = threading.Thread(target=_run_linkedin, args=(li_notify,), name="LinkedIn", daemon=True)
            threads.append(t)

        # Thread 2: Selenium group (Internshala + Naukri + Hirist + Foundit)
        sel_active = [s for s in active if s in ("Internshala", "Naukri", "Hirist", "Foundit")]
        if sel_active:
            t = threading.Thread(target=_run_selenium_group, args=(sel_notify,), name="Selenium", daemon=True)
            threads.append(t)

        # Thread 3: HTTP scrapers
        http_active = [s for s in active if s not in ("LinkedIn", "Internshala", "Naukri", "Hirist", "Foundit")]
        if http_active:
            t = threading.Thread(target=_run_http_scrapers, args=(http_notify,), name="HTTP", daemon=True)
            threads.append(t)



        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Tally results
        total_found = li_notify.get_counts()["found"] + sel_notify.get_counts()["found"] + http_notify.get_counts()["found"]
        total_new = li_notify.get_counts()["new"] + sel_notify.get_counts()["new"] + http_notify.get_counts()["new"]

        finish_scrape_run(run_id, total_found, total_new)
        _set_status("idle")
        _log(f"Cycle complete. Found {total_found} jobs, {total_new} new.")

        return {"jobs_found": total_found, "new_jobs": total_new, "sources": active}

    except Exception as e:
        _set_status("error")
        _log(f"[ERROR] Scrape cycle failed: {e}")
        try:
            finish_scrape_run(run_id, 0, 0, "error")
        except Exception:
            pass
        return {"error": str(e)}
    finally:
        _scrape_lock.release()


# ── Main loop ──────────────────────────────────────────────────────────

def main():
    from database import init_db
    init_db()

    if not DISCORD_WEBHOOK_URL:
        _log("[WARN] DISCORD_WEBHOOK_URL is not set — Discord notifications disabled.")

    once = "--once" in sys.argv

    # Startup sweep
    if not _shutdown.is_set():
        _log(f"{'=' * 55}")
        _log(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Running startup 24h sweep")
        _log(f"{'=' * 55}")
        li_notify = _make_instant_notifier("LinkedIn")
        _run_startup_sweep(li_notify)

    while not _shutdown.is_set():
        run_scrape_cycle()

        if _shutdown.is_set():
            break
        if once:
            _log("Done (--once mode).")
            break
        if RUN_INTERVAL > 0:
            _log(f"Next run in {RUN_INTERVAL}s...")
            _shutdown.wait(timeout=RUN_INTERVAL)
        else:
            _log("Starting next cycle immediately...")

    _log("[INFO] Cleaning up drivers...")
    from driver import close_all_drivers
    close_all_drivers()
    _log("[INFO] Shutdown complete.")


if __name__ == "__main__":
    main()
