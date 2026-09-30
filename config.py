import os

from dotenv import load_dotenv

load_dotenv()

# Discord webhook URL
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

# Google Sheets Webhook URL (optional, for auto-syncing jobs to Google Sheets)
GOOGLE_SHEET_WEBHOOK_URL = os.environ.get("GOOGLE_SHEET_WEBHOOK_URL", "")

# Jooble API key (free from https://jooble.org/api/about)
JOOBLE_API_KEY = os.environ.get("JOOBLE_API_KEY", "")


# ── Search settings ────────────────────────────────────────────────────
SEARCH_KEYWORDS = [
    "Flutter Developer",
    "Flutter Engineer",
    "Dart Developer",
    "Mobile Developer Flutter",
    "Junior Flutter Developer",
    "Flutter Intern",
    "Flutter Mobile Developer",
    "Cross Platform Developer Flutter",
]

# Relevant domain terms — job title must strictly relate to Flutter/Dart or Mobile
RELEVANT_TITLE_TERMS = [
    "flutter", "dart", "mobile", "android", "ios",
    "cross-platform", "cross platform",
    "mobile app", "mobile application", "mobile developer", "mobile engineer",
    "app developer", "app engineer",
]


# Location for job search
LOCATION = "Bengaluru, Karnataka, India"

# f_TPR filter: r600 = jobs posted in last 10 minutes
TIME_FILTER = "r600"

# Startup sweep: one 24-hour search per keyword when the project starts
STARTUP_TIME_FILTER = "r86400"          # 24 hours in seconds
STARTUP_MAX_JOB_AGE_HOURS = 24          # allow jobs up to 24h old during startup

# 5-minute gap between each full pass of all keywords
RUN_INTERVAL = 300

# 20-40s between each keyword search (Selenium-based scrapers)
SEARCH_DELAY_MIN = 20
SEARCH_DELAY_MAX = 40

# Max age of job posting to notify (in hours)
MAX_JOB_AGE_HOURS = 3

# Experience level filter: 1 = Internship, 2 = Entry level, 3 = Associate
EXPERIENCE_LEVELS = ["1", "2"]

# Blacklisted companies — jobs from these are skipped
BLACKLISTED_COMPANIES = [
    "skoollage",
    "dexter's tech",
    "sportsbuzz",
    "webs it solution",
    "zenithbyte",
    "skillzenloop",
    "Webs X UM",
    "inficore soft",
    "VEDIST SYSTEMS PRIVATE LIMITED",
    "Uplers",
    "Atricu MakeuspeakEdtech",
    "Binated",
    "scoutit",
    "ge vernova",
    "uplers",
]

# Blacklisted title keywords — jobs with these in the title are skipped
BLACKLISTED_TITLE_KEYWORDS = [
    # Seniority / management
    "senior", "sr.", "sr ", "lead", "principal", "staff", "manager",
    "director", "head of", "vp ", "vice president", "architect",
    "management", "managing", "program manager", "project manager",
    "product manager", "account manager", "team lead",
    # Experience levels (too high for 1 yr experience)
    "10+", "8+", "7+", "6+", "5+", "4+", "3+",
    "14+", "12+", "11+", "9+",
    "l4", "l5", "l6", "l7",
    "sde 3", "sde3", "sde-3", "sde iii", "sde-iii",
    "sde 2", "sde2", "sde-2", "sde ii", "sde-ii",
    "engineer ii", "engineer 2", "developer ii", "developer 2", "level 2", "level ii",
    # Non-Flutter language stacks
    "c++", "cpp", "java developer", "python developer", "golang", "ruby on rails", "rust developer",
    ".net developer", "dotnet", "php developer", "angular",

    # Unrelated roles
    "content writer", "content writing", "copywriter", "article writer",
    "technical writer", "blog writer", "editor",
    "sales", "business development", "bde", "bda",
    "marketing", "digital marketing", "seo", "sem",
    "hr ", "human resource", "recruiter", "recruitment",
    "finance", "accounting", "accountant", "chartered",
    "teacher", "trainer", "faculty", "professor", "tutor",
    "customer support", "customer service", "helpdesk",
    "telecaller", "telesales", "call center",
    "civil engineer", "mechanical engineer", "electrical engineer",
    "pharmacy", "medical", "nurse", "doctor",
    "data scientist", "data science", "machine learning",
]

# ── Enable/disable job sites ──────────────────────────────────────────
ENABLE_LINKEDIN = True
ENABLE_INTERNSHALA = True
ENABLE_NAUKRI = True
ENABLE_INSTAHYRE = True
ENABLE_HIRINGCAFE = True
ENABLE_YCOMBINATOR = True
ENABLE_WELLFOUND = True
ENABLE_INDEED = True
ENABLE_ZIPRECRUITER = True
ENABLE_GLASSDOOR = True
ENABLE_CUTSHORT = True
ENABLE_DICE = True
ENABLE_CAREERJET = True
ENABLE_OTTA = True
ENABLE_PEERLIST = True
ENABLE_ARC = True
ENABLE_UNSTOP = True
ENABLE_ACCIOJOBS = True
ENABLE_ONEROADMAP = True
ENABLE_HIRIST = True
ENABLE_WEWORKREMOTELY = True
ENABLE_A16Z = True
ENABLE_FOUNDIT = True
ENABLE_JOOBLE = True
ENABLE_OFFCAMPUSJOBDRIVES = True


# ── Dashboard settings ─────────────────────────────────────────────────
ENABLE_DASHBOARD = True
DASHBOARD_PORT = 5000