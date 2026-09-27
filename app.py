"""
app.py — Flask dashboard + REST API for the job scraper.

Single entry point: `python app.py` starts the dashboard AND the scraper engine.
"""

import json
import threading
import time

from flask import Flask, Response, jsonify, render_template, request, stream_with_context

from config import DASHBOARD_PORT
from database import (
    export_jobs_csv,
    get_jobs,
    get_stats,
    init_db,
    update_job_status,
)
from main import (
    _shutdown,
    get_scrape_status,
    main as scraper_main,
    run_scrape_cycle,
    subscribe_logs,
    unsubscribe_logs,
)

app = Flask(__name__)


# ── Page routes ────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ── API: Jobs ──────────────────────────────────────────────────────────

@app.route("/api/jobs")
def api_jobs():
    result = get_jobs(
        source=request.args.get("source"),
        status=request.args.get("status"),
        keyword=request.args.get("keyword"),
        search=request.args.get("search"),
        page=int(request.args.get("page", 1)),
        per_page=int(request.args.get("per_page", 20)),
        sort_by=request.args.get("sort_by", "found_at"),
        sort_dir=request.args.get("sort_dir", "desc"),
    )
    return jsonify(result)


@app.route("/api/jobs/<job_id>", methods=["PATCH"])
def api_update_job(job_id):
    data = request.get_json(silent=True) or {}
    ok = update_job_status(
        job_id,
        status=data.get("status"),
        notes=data.get("notes"),
    )
    if ok:
        return jsonify({"success": True})
    return jsonify({"error": "invalid status or job not found"}), 400


# ── API: Stats ─────────────────────────────────────────────────────────

@app.route("/api/stats")
def api_stats():
    return jsonify(get_stats())


# ── API: Export ────────────────────────────────────────────────────────

@app.route("/api/export")
def api_export():
    csv_str = export_jobs_csv(
        source=request.args.get("source"),
        status=request.args.get("status"),
        keyword=request.args.get("keyword"),
        search=request.args.get("search"),
    )
    return Response(
        csv_str,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=jobs_export.csv"},
    )


# ── API: Scrape control ───────────────────────────────────────────────

@app.route("/api/scrape", methods=["POST"])
def api_scrape():
    status = get_scrape_status()
    if status["state"] == "running":
        return jsonify({"error": "Scrape already in progress"}), 409

    data = request.get_json(silent=True) or {}
    sources = data.get("sources")  # optional list

    # Run in background thread
    def _bg():
        run_scrape_cycle(sources=sources)

    threading.Thread(target=_bg, daemon=True, name="ManualScrape").start()
    return jsonify({"message": "Scrape started", "sources": sources or "all"})


@app.route("/api/scrape/status")
def api_scrape_status():
    return jsonify(get_scrape_status())


# ── API: Config (read-only) ───────────────────────────────────────────

@app.route("/api/config")
def api_config():
    from config import (
        ENABLE_INTERNSHALA,
        ENABLE_LINKEDIN,
        ENABLE_NAUKRI,
        LOCATION,
        RUN_INTERVAL,
        SEARCH_KEYWORDS,
    )
    return jsonify({
        "keywords": SEARCH_KEYWORDS,
        "location": LOCATION,
        "run_interval": RUN_INTERVAL,
        "sources": {
            "LinkedIn": ENABLE_LINKEDIN,
            "Internshala": ENABLE_INTERNSHALA,
            "Naukri": ENABLE_NAUKRI,
        },
    })


# ── API: Live log stream (SSE) ────────────────────────────────────────

@app.route("/api/logs")
def api_logs():
    def stream():
        evt, buf = subscribe_logs()
        last_idx = len(buf)

        try:
            # Send existing buffer first
            for line in list(buf):
                yield f"data: {json.dumps({'msg': line})}\n\n"

            while True:
                evt.wait(timeout=2)
                evt.clear()

                # Send any new entries
                current = list(buf)
                if len(current) > last_idx:
                    for line in current[last_idx:]:
                        yield f"data: {json.dumps({'msg': line})}\n\n"
                    last_idx = len(current)
                elif len(current) < last_idx:
                    # Buffer wrapped around
                    for line in current:
                        yield f"data: {json.dumps({'msg': line})}\n\n"
                    last_idx = len(current)

                # Heartbeat
                yield f": keepalive\n\n"

        except GeneratorExit:
            pass
        finally:
            unsubscribe_logs(evt)

    return Response(
        stream_with_context(stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── Startup ────────────────────────────────────────────────────────────

def main():
    init_db()

    # Start the scraper engine in a background daemon thread
    scraper_thread = threading.Thread(target=scraper_main, daemon=True, name="ScraperEngine")
    scraper_thread.start()

    print(f"\n{'=' * 55}")
    print(f"  Job Scraper Dashboard")
    print(f"  http://localhost:{DASHBOARD_PORT}")
    print(f"{'=' * 55}\n")

    app.run(
        host="0.0.0.0",
        port=DASHBOARD_PORT,
        debug=False,
        use_reloader=False,
    )


if __name__ == "__main__":
    main()
