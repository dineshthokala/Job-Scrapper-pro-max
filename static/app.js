/* ═══════════════════════════════════════════════════════════════════════
   Job Scraper Dashboard — Client-side Logic
   ═══════════════════════════════════════════════════════════════════════ */

// ── State ─────────────────────────────────────────────────────────────

let currentPage = 1;
let currentSort = "found_at";
let currentSortDir = "desc";
let debounceTimer = null;
let logLineCount = 0;

const PER_PAGE = 20;
const STATUS_OPTIONS = ["new", "saved", "applied", "interviewing", "rejected", "offer"];
const SOURCE_COLORS = {
    "LinkedIn":   "#0a66c2",
    "Naukri":     "#2d69f0",
    "Internshala":"#00a5ec",
};


// ── Init ──────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
    fetchStats();
    fetchJobs();
    setupSorting();
    connectLogStream();
    pollScrapeStatus();

    // Refresh stats every 30s
    setInterval(fetchStats, 30000);
    // Refresh scrape status every 5s
    setInterval(pollScrapeStatus, 5000);
});


// ── Stats ─────────────────────────────────────────────────────────────

async function fetchStats() {
    try {
        const resp = await fetch("/api/stats");
        const data = await resp.json();

        document.getElementById("statTotal").textContent = data.total.toLocaleString();
        document.getElementById("statToday").textContent = data.today.toLocaleString();
        document.getElementById("statSaved").textContent = (data.by_status.saved || 0).toLocaleString();
        document.getElementById("statApplied").textContent = (data.by_status.applied || 0).toLocaleString();

        const interviewCount = data.by_status.interviewing || 0;
        const offerCount = data.by_status.offer || 0;
        document.getElementById("statInterviewing").textContent =
            `${interviewCount} interviewing · ${offerCount} offers`;

        // Source chips
        const chipsEl = document.getElementById("sourceChips");
        chipsEl.innerHTML = "";
        for (const [src, cnt] of Object.entries(data.by_source)) {
            const color = SOURCE_COLORS[src] || "#64748b";
            chipsEl.innerHTML += `
                <span class="source-chip">
                    <span class="chip-dot" style="background:${color}"></span>
                    ${src}: ${cnt}
                </span>`;
        }

        // Populate source filter dropdown
        const sourceFilter = document.getElementById("sourceFilter");
        const currentVal = sourceFilter.value;
        sourceFilter.innerHTML = '<option value="">All Sources</option>';
        (data.sources || []).forEach(src => {
            sourceFilter.innerHTML += `<option value="${src}" ${src === currentVal ? "selected" : ""}>${src}</option>`;
        });

        // Populate keyword filter dropdown
        const keywordFilter = document.getElementById("keywordFilter");
        const currentKw = keywordFilter.value;
        keywordFilter.innerHTML = '<option value="">All Keywords</option>';
        (data.keywords || []).forEach(kw => {
            keywordFilter.innerHTML += `<option value="${kw}" ${kw === currentKw ? "selected" : ""}>${kw}</option>`;
        });

    } catch (err) {
        console.error("Failed to fetch stats:", err);
    }
}


// ── Jobs ──────────────────────────────────────────────────────────────

async function fetchJobs() {
    const params = new URLSearchParams({
        page: currentPage,
        per_page: PER_PAGE,
        sort_by: currentSort,
        sort_dir: currentSortDir,
    });

    const search = document.getElementById("searchInput").value.trim();
    const source = document.getElementById("sourceFilter").value;
    const status = document.getElementById("statusFilter").value;
    const keyword = document.getElementById("keywordFilter").value;

    if (search) params.set("search", search);
    if (source) params.set("source", source);
    if (status) params.set("status", status);
    if (keyword) params.set("keyword", keyword);

    try {
        const resp = await fetch(`/api/jobs?${params}`);
        const data = await resp.json();
        renderJobs(data);
    } catch (err) {
        console.error("Failed to fetch jobs:", err);
    }
}

function debouncedFetch() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
        currentPage = 1;
        fetchJobs();
    }, 300);
}

function renderJobs(data) {
    const tbody = document.getElementById("jobTableBody");
    const emptyState = document.getElementById("emptyState");
    const tableWrap = document.querySelector(".table-wrap");
    const jobCount = document.getElementById("jobCount");

    jobCount.textContent = `(${data.total.toLocaleString()})`;

    if (data.jobs.length === 0) {
        tbody.innerHTML = "";
        tableWrap.style.display = "none";
        emptyState.style.display = "block";
        document.getElementById("pagination").style.display = "none";
        return;
    }

    tableWrap.style.display = "block";
    emptyState.style.display = "none";
    document.getElementById("pagination").style.display = "flex";

    tbody.innerHTML = data.jobs.map(job => `
        <tr data-job-id="${escHtml(job.job_id)}">
            <td><span class="source-badge ${getSourceClass(job.source)}">${escHtml(job.source)}</span></td>
            <td>
                <a class="job-title-link" href="${escHtml(job.url)}" target="_blank" rel="noopener">
                    ${escHtml(job.title)}
                </a>
            </td>
            <td class="job-company">${escHtml(job.company)}</td>
            <td class="job-location">${escHtml(job.location)}</td>
            <td class="job-location">${escHtml(job.keyword)}</td>
            <td class="job-time">${formatTime(job.found_at)}</td>
            <td>
                <select class="status-select ${job.status}" onchange="updateStatus('${escHtml(job.job_id)}', this.value, this)">
                    ${STATUS_OPTIONS.map(s =>
                        `<option value="${s}" ${s === job.status ? "selected" : ""}>${s}</option>`
                    ).join("")}
                </select>
            </td>
            <td class="notes-cell">
                <button class="notes-btn ${job.notes ? 'has-notes' : ''}" onclick="toggleNotes(this, '${escHtml(job.job_id)}', ${escAttr(JSON.stringify(job.notes || ''))})">
                    📝
                </button>
            </td>
        </tr>
    `).join("");

    // Pagination
    renderPagination(data);
}

function renderPagination(data) {
    const from = (data.page - 1) * data.per_page + 1;
    const to = Math.min(data.page * data.per_page, data.total);

    document.getElementById("pageFrom").textContent = from;
    document.getElementById("pageTo").textContent = to;
    document.getElementById("pageTotal").textContent = data.total;

    const btnsEl = document.getElementById("pageButtons");
    let html = "";

    // Prev
    html += `<button class="page-btn" ${data.page <= 1 ? "disabled" : ""} onclick="goToPage(${data.page - 1})">‹</button>`;

    // Page numbers
    const maxBtns = 7;
    let start = Math.max(1, data.page - Math.floor(maxBtns / 2));
    let end = Math.min(data.pages, start + maxBtns - 1);
    start = Math.max(1, end - maxBtns + 1);

    if (start > 1) {
        html += `<button class="page-btn" onclick="goToPage(1)">1</button>`;
        if (start > 2) html += `<button class="page-btn" disabled>…</button>`;
    }

    for (let i = start; i <= end; i++) {
        html += `<button class="page-btn ${i === data.page ? "active" : ""}" onclick="goToPage(${i})">${i}</button>`;
    }

    if (end < data.pages) {
        if (end < data.pages - 1) html += `<button class="page-btn" disabled>…</button>`;
        html += `<button class="page-btn" onclick="goToPage(${data.pages})">${data.pages}</button>`;
    }

    // Next
    html += `<button class="page-btn" ${data.page >= data.pages ? "disabled" : ""} onclick="goToPage(${data.page + 1})">›</button>`;

    btnsEl.innerHTML = html;
}

function goToPage(page) {
    currentPage = page;
    fetchJobs();
    document.getElementById("jobsCard").scrollIntoView({ behavior: "smooth", block: "start" });
}


// ── Sorting ───────────────────────────────────────────────────────────

function setupSorting() {
    document.querySelectorAll(".job-table th[data-sort]").forEach(th => {
        th.addEventListener("click", () => {
            const field = th.dataset.sort;
            if (currentSort === field) {
                currentSortDir = currentSortDir === "desc" ? "asc" : "desc";
            } else {
                currentSort = field;
                currentSortDir = field === "found_at" ? "desc" : "asc";
            }

            // Update header visuals
            document.querySelectorAll(".job-table th").forEach(h => h.classList.remove("sorted"));
            th.classList.add("sorted");
            th.querySelector(".sort-arrow").textContent = currentSortDir === "asc" ? "▲" : "▼";

            currentPage = 1;
            fetchJobs();
        });
    });
}


// ── Status update ─────────────────────────────────────────────────────

async function updateStatus(jobId, newStatus, selectEl) {
    // Update visual class immediately
    selectEl.className = `status-select ${newStatus}`;

    try {
        const resp = await fetch(`/api/jobs/${encodeURIComponent(jobId)}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: newStatus }),
        });
        if (resp.ok) {
            toast(`Status updated to "${newStatus}"`, "success");
            fetchStats();
        } else {
            toast("Failed to update status", "error");
        }
    } catch (err) {
        toast("Network error", "error");
    }
}


// ── Notes popup ───────────────────────────────────────────────────────

function toggleNotes(btn, jobId, currentNotes) {
    // Close any other open popups
    document.querySelectorAll(".notes-popup.active").forEach(p => p.remove());

    const popup = document.createElement("div");
    popup.className = "notes-popup active";
    popup.innerHTML = `
        <textarea class="notes-textarea" placeholder="Add notes...">${currentNotes}</textarea>
        <button class="btn btn-sm btn-primary notes-save" onclick="saveNotes('${jobId}', this)">Save</button>
    `;
    btn.parentElement.appendChild(popup);

    // Focus textarea
    popup.querySelector("textarea").focus();

    // Close on click outside
    setTimeout(() => {
        document.addEventListener("click", function closePopup(e) {
            if (!popup.contains(e.target) && e.target !== btn) {
                popup.remove();
                document.removeEventListener("click", closePopup);
            }
        });
    }, 10);
}

async function saveNotes(jobId, btn) {
    const popup = btn.closest(".notes-popup");
    const notes = popup.querySelector("textarea").value;

    try {
        const resp = await fetch(`/api/jobs/${encodeURIComponent(jobId)}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ notes }),
        });
        if (resp.ok) {
            toast("Notes saved", "success");
            popup.remove();
            // Update the notes button indicator
            const row = document.querySelector(`tr[data-job-id="${jobId}"]`);
            if (row) {
                const notesBtn = row.querySelector(".notes-btn");
                notesBtn.classList.toggle("has-notes", notes.trim().length > 0);
            }
        } else {
            toast("Failed to save notes", "error");
        }
    } catch (err) {
        toast("Network error", "error");
    }
}


// ── Filters ───────────────────────────────────────────────────────────

function resetFilters() {
    document.getElementById("searchInput").value = "";
    document.getElementById("sourceFilter").value = "";
    document.getElementById("statusFilter").value = "";
    document.getElementById("keywordFilter").value = "";
    currentPage = 1;
    currentSort = "found_at";
    currentSortDir = "desc";
    fetchJobs();
}

function exportCSV() {
    const params = new URLSearchParams();
    const search = document.getElementById("searchInput").value.trim();
    const source = document.getElementById("sourceFilter").value;
    const status = document.getElementById("statusFilter").value;
    const keyword = document.getElementById("keywordFilter").value;

    if (search) params.set("search", search);
    if (source) params.set("source", source);
    if (status) params.set("status", status);
    if (keyword) params.set("keyword", keyword);

    window.open(`/api/export?${params}`, "_blank");
    toast("CSV download started", "info");
}


// ── Scrape control ────────────────────────────────────────────────────

async function triggerScrape() {
    const btn = document.getElementById("scrapeBtn");
    btn.disabled = true;
    btn.textContent = "⏳ Starting...";

    try {
        const resp = await fetch("/api/scrape", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
        });
        const data = await resp.json();
        if (resp.ok) {
            toast("Scrape started!", "success");
            updateScrapeUI("running");
        } else {
            toast(data.error || "Failed to start scrape", "error");
            btn.disabled = false;
            btn.textContent = "⚡ Run Scrape";
        }
    } catch (err) {
        toast("Network error", "error");
        btn.disabled = false;
        btn.textContent = "⚡ Run Scrape";
    }
}

async function pollScrapeStatus() {
    try {
        const resp = await fetch("/api/scrape/status");
        const data = await resp.json();
        updateScrapeUI(data.state, data.last_run);
    } catch (err) {
        // ignore
    }
}

function updateScrapeUI(state, lastRun) {
    const dot = document.getElementById("statusDot");
    const text = document.getElementById("statusText");
    const btn = document.getElementById("scrapeBtn");
    const lastRunBadge = document.getElementById("lastRunBadge");

    dot.className = "status-dot";
    if (state === "running") {
        dot.classList.add("running");
        text.textContent = "Scraping...";
        btn.disabled = true;
        btn.innerHTML = "⏳ Running...";
    } else if (state === "error") {
        dot.classList.add("error");
        text.textContent = "Error";
        btn.disabled = false;
        btn.innerHTML = "⚡ Run Scrape";
    } else {
        text.textContent = "Idle";
        btn.disabled = false;
        btn.innerHTML = "⚡ Run Scrape";
        // Refresh jobs and stats when a scrape completes
        fetchJobs();
        fetchStats();
    }

    if (lastRun) {
        lastRunBadge.style.display = "inline-flex";
        document.getElementById("lastRunTime").textContent = formatTime(lastRun);
    }
}


// ── Log terminal ──────────────────────────────────────────────────────

function toggleTerminal() {
    const toggle = document.getElementById("termToggle");
    const body = document.getElementById("termBody");
    const isOpen = toggle.classList.toggle("open");
    body.classList.toggle("open", isOpen);
}

function connectLogStream() {
    const output = document.getElementById("termOutput");
    const logCountEl = document.getElementById("logCount");

    const source = new EventSource("/api/logs");

    source.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            const line = document.createElement("span");
            line.className = `log-line ${classifyLog(data.msg)}`;
            line.textContent = data.msg;
            output.appendChild(line);
            logLineCount++;
            logCountEl.textContent = `${logLineCount} lines`;

            // Auto-scroll if near bottom
            const isNearBottom = output.scrollHeight - output.scrollTop - output.clientHeight < 60;
            if (isNearBottom) {
                output.scrollTop = output.scrollHeight;
            }

            // Limit DOM lines
            while (output.children.length > 600) {
                output.removeChild(output.firstChild);
            }
        } catch (e) {
            // ignore parse errors
        }
    };

    source.onerror = () => {
        setTimeout(() => connectLogStream(), 3000);
        source.close();
    };
}

function classifyLog(msg) {
    const m = msg.toLowerCase();
    if (m.includes("[error]")) return "error";
    if (m.includes("[warn]")) return "warn";
    if (m.includes("[skip]")) return "skip";
    if (m.includes("[notify]")) return "notify";
    if (m.includes("[new]")) return "new";
    if (m.includes("[info]")) return "info";
    if (m.includes("===")) return "sep";
    return "";
}


// ── Toasts ────────────────────────────────────────────────────────────

function toast(message, type = "info") {
    const container = document.getElementById("toastContainer");
    const t = document.createElement("div");
    t.className = `toast ${type}`;
    t.textContent = message;
    container.appendChild(t);
    setTimeout(() => t.remove(), 3000);
}


// ── Utilities ─────────────────────────────────────────────────────────

function escHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

function escAttr(str) {
    return str.replace(/'/g, "\\'").replace(/"/g, "&quot;");
}

function getSourceClass(source) {
    if (!source) return "default";
    const s = source.toLowerCase().replace(/\s+/g, "");
    const map = {
        "linkedin": "linkedin",
        "naukri": "naukri",
        "internshala": "internshala",
        "indeed": "indeed",
        "glassdoor": "glassdoor",
        "wellfound": "wellfound",
        "ycombinator": "ycombinator",
        "instahyre": "instahyre",
        "cutshort": "cutshort",
        "dice": "dice",
        "careerjet": "careerjet",
        "ziprecruiter": "ziprecruiter",
        "hiringcafe": "hiringcafe",
        "otta": "otta",
        "peerlist": "peerlist",
        "arc": "arc",
        "unstop": "unstop",
        "acciojobs": "acciojobs",
    };
    return map[s] || "default";
}

function formatTime(isoStr) {
    if (!isoStr) return "—";
    try {
        const d = new Date(isoStr);
        if (isNaN(d.getTime())) return isoStr;

        const now = new Date();
        const diffMs = now - d;
        const diffMin = Math.floor(diffMs / 60000);
        const diffHr = Math.floor(diffMs / 3600000);
        const diffDay = Math.floor(diffMs / 86400000);

        if (diffMin < 1) return "Just now";
        if (diffMin < 60) return `${diffMin}m ago`;
        if (diffHr < 24) return `${diffHr}h ago`;
        if (diffDay < 7) return `${diffDay}d ago`;

        return d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
    } catch {
        return isoStr;
    }
}
