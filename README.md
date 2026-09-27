# Job Scraper Dashboard

A powerful, parallel job scraping tool for **18 different job portals** (LinkedIn, Naukri, Internshala, Wellfound, YCombinator, Instahyre, Glassdoor, Indeed, and more). It includes a beautiful web dashboard to track jobs, apply statuses, and view live logs, along with instant Discord notifications.

## Features

- **Web Dashboard** — A modern, dark-themed UI at `http://localhost:5000` to view, filter, sort, and manage all scraped jobs.
- **18 Supported Portals** — Scrapes LinkedIn, Naukri, Internshala, Indeed, Glassdoor, Wellfound, YCombinator, Instahyre, Cutshort, Dice, CareerJet, ZipRecruiter, HiringCafe, Otta, Peerlist, Arc, Unstop, and AccioJobs.
- **Parallel Scraping** — Runs multiple scrapers concurrently (Selenium for heavy sites, lightweight HTTP requests for others).
- **SQLite Database** — All jobs and your application statuses are saved to `jobs.db`.
- **Instant Discord Alerts** — Jobs are sent to a Discord channel the moment they're found.
- **Smart Filtering** — Filters by title keywords (e.g., Flutter, Dart), company blacklist, location (including remote), and posting age.

## Setup Instructions

1. **Clone or Download** the repository to your local machine.
2. **Create a virtual environment** (recommended) and install dependencies:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate     # On Windows
   pip install -r requirements.txt
   ```
3. **Configure `.env`** (Optional but recommended for notifications):
   Create a `.env` file in the main folder with your Discord webhook URL:
   ```
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
   ```
4. **Edit `config.py`** to customize your search:
   - Modify `SEARCH_KEYWORDS` for your target roles.
   - Adjust `LOCATION` or add allowed locations in `driver.py` (Remote/WFH is supported).
   - Toggle specific job portals using the `ENABLE_*` flags.

## Step-by-Step Guide to Start

To start the scraper and the web dashboard:

1. Open your terminal or command prompt.
2. Ensure you are in the project folder and your virtual environment is activated:
   ```bash
   .venv\Scripts\activate
   ```
3. Run the Flask application:
   ```bash
   python app.py
   ```
4. Open your web browser and navigate to:
   **[http://localhost:5000](http://localhost:5000)**

The scraper will immediately run a "startup sweep" to catch jobs posted in the last 24 hours, and then it will continuously run every 5 minutes (or as configured in `config.py`). You can also manually trigger a scrape from the dashboard using the "⚡ Run Scrape" button.

## FAQ

**Will the scraping stop if I shut down my laptop?**
Yes. Because this script runs entirely on your local machine, the scraping process and the web dashboard will stop running the moment your laptop turns off or goes to sleep. 

---

## 24/7 Cloud Hosting (100% Free, NO Credit Card Required!)

You can run the scraper in the cloud using **GitHub Actions**. It runs on GitHub's cloud servers every 2 hours, requires **no credit card**, and sends Discord alerts straight to your phone.

### Quick Setup:

1. **Push this project to a GitHub repository** (make it Private so your webhook is hidden):
   ```bash
   git init
   git add .
   git commit -m "Add job scraper with GitHub Actions"
   git branch -M main
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

2. **Add your Discord Webhook as a Secret**:
   - Go to your repository on GitHub.
   - Click **Settings** ➔ **Secrets and variables** ➔ **Actions**.
   - Click **New repository secret**.
   - **Name**: `DISCORD_WEBHOOK_URL`
   - **Secret**: Paste your Discord Webhook URL.
   - Click **Add secret**.

3. **Enable Write Permissions (to persist `jobs.db`)**:
   - Go to **Settings** ➔ **Actions** ➔ **General**.
   - Scroll down to **Workflow permissions**.
   - Select **Read and write permissions** and click **Save**.

4. **That's it!**
   - The scraper will automatically run every 2 hours in the cloud.
   - You can also manually trigger it anytime by going to the **Actions** tab on GitHub, clicking **24/7 Flutter Job Scraper**, and clicking **Run workflow**.

---

## Google Sheets Tracking (Auto-Sync)

You can automatically send every newly discovered job to a **Google Sheet** so you can track your applications on your phone or laptop.

### Setup (2 Minutes, No API Keys Needed):
1. Create a new Google Sheet named **"Flutter Job Tracker"**.
2. Click **Extensions** ➔ **Apps Script**.
3. Delete any code and paste the code from [`google_apps_script.js`](google_apps_script.js).
4. Click **Deploy** (top right) ➔ **New deployment**:
   - Select type: **Web app**
   - Execute as: **Me**
   - Who has access: **Anyone**
5. Click **Deploy**, authorize permissions, and copy the **Web app URL**.
6. Add that URL:
   - In `.env`: `GOOGLE_SHEET_WEBHOOK_URL=https://script.google.com/macros/s/.../exec`
   - In GitHub Secrets: Add `GOOGLE_SHEET_WEBHOOK_URL` so cloud runs also update your sheet!

Now, whenever a new Flutter job is scraped, a row is automatically added to your Google Sheet with the date, job title, company, source, and direct link!


---

## Alternative: Oracle Cloud Always Free VM (Requires Credit Card)

To run the backend 24/7 without your laptop staying on (scraping ➔ instant Discord messages):

### 1. Create your Free VM in Oracle Cloud
1. Sign up for **[Oracle Cloud Always Free](https://www.oracle.com/cloud/free/)**.
2. Go to **Compute** ➔ **Instances** ➔ **Create Instance**.
3. **Image**: Choose `Canonical Ubuntu 22.04` or `24.04`.
4. **Shape**: Choose `VM.Standard.E2.1.Micro` (Always Free eligible) or `Ampere A1`.
5. **SSH Keys**: Download your private key (`.key`) to your computer.
6. Click **Create** and copy your **Public IP Address**.

### 2. Connect from Windows PowerShell
```powershell
ssh -i "path\to\your-key.key" ubuntu@YOUR_VM_PUBLIC_IP
```

### 3. Deploy the Scraper
Run the following commands inside the VM terminal:
```bash
# Clone the repository
git clone <your-repo-url> Linkdin_Scraper
cd Linkdin_Scraper

# Run automated environment setup
chmod +x setup_vps.sh
./setup_vps.sh

# Add your Discord Webhook URL in .env
echo "DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/..." > .env
```

### 4. Enable 24/7 Background Execution (`systemd`)
To keep the scraper running forever (even after reboots):
```bash
sudo cp scraper.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable scraper
sudo systemctl start scraper
```

* **Check status**: `sudo systemctl status scraper`
* **View live logs**: `tail -f scraper.log`
* **Stop scraper**: `sudo systemctl stop scraper`

