from pathlib import Path

PROJECT_DIR = Path(__file__).parent
DATA_DIR    = PROJECT_DIR / "data"
OUTPUT_DIR  = PROJECT_DIR / "output"

# ── URLs ─────────────────────────────────────────────────────────────────────
START_URL  = "https://www.get-in-it.de/it-jobs-berlin"
SEARCH_URL = "https://www.get-in-it.de/jobsuche?city=6176&radius=25"
BASE_URL   = "https://www.get-in-it.de"

# ── Scraper ───────────────────────────────────────────────────────────────────
CONCURRENCY      = 8
PAGE_TIMEOUT     = 30_000   # ms
SKIP_BADGE_TEXTS = {"Tipp", "Neu", "Top"}

# ── Dateipfade ────────────────────────────────────────────────────────────────
RAW_CSV      = DATA_DIR / "jobs_berlin_raw.csv"
ENRICHED_CSV = DATA_DIR / "jobs_berlin_enriched.csv"
CHART_PNG    = OUTPUT_DIR / "skills_chart.png"

# ── Visualisierung ────────────────────────────────────────────────────────────
TOP_N_SKILLS = 30
