# get-in-IT Job Scraper

Scrapes all IT job listings from [get-in-it.de/it-jobs-berlin](https://www.get-in-it.de/it-jobs-berlin), extracts and normalizes hard skills from job descriptions, and generates a ranked skill-frequency chart — ready for portfolio gap analysis.

---

## Setup

```bash
# 1. Abhängigkeiten installieren
pip install -r requirements.txt

# 2. Playwright-Browser herunterladen (einmalig)
playwright install chromium
```

---

## Nutzung

```bash
# Komplette Pipeline (empfohlen beim ersten Start)
python main.py --all

# Einzelne Schritte
python main.py --scrape       # Rohdaten scrapen  → data/jobs_berlin_raw.csv
python main.py --enrich       # Skills anreichern → data/jobs_berlin_enriched.csv
python main.py --visualize    # Diagramm erstellen → output/skills_chart.png

# Schritte kombinieren
python main.py --enrich --visualize
```

> **Hinweis:** `--enrich` setzt `data/jobs_berlin_raw.csv` voraus (zuerst `--scrape` ausführen).  
> `--visualize` setzt `data/jobs_berlin_enriched.csv` voraus (zuerst `--enrich` ausführen).

---

## Architektur

```
get-in-it.de
    │
    ▼
scraper.py          Playwright (headless Chromium)
                    • Lädt https://get-in-it.de/it-jobs-berlin
                    • Klickt "Mehr anzeigen" bis alle ~850 Jobs geladen
                    • Scrapet Firmenname, Titel, Beschreibung, Badge-Skills
                    │
                    ▼
            data/jobs_berlin_raw.csv
                    │
                    ▼
extract_skills.py   Regex-Engine (~150 Skill-Pattern)
                    • Scannt position_description auf Hard Skills
                    • Merged Badge-Skills + Text-Skills
                    • Entfernt Nahe-Duplikate (Substring-Dedup)
                    │
                    ▼
            data/jobs_berlin_enriched.csv
                    │
                    ▼
visualize_skills.py matplotlib
                    • Top-30 Skills nach Häufigkeit
                    • Farbcodiert nach Kategorie
                    │
                    ▼
            output/skills_chart.png
```

---

## Output-Dateien

| Datei | Inhalt |
|---|---|
| `data/jobs_berlin_raw.csv` | Rohdaten: `company_name`, `position_name`, `position_description`, `skills` (Badge-Chips) |
| `data/jobs_berlin_enriched.csv` | Gleiche Spalten, `skills` um aus Beschreibungstext extrahierte Hard Skills erweitert |
| `output/skills_chart.png` | Horizontales Balkendiagramm, Top 30 Skills, farbcodiert nach Kategorie |

---

## Konfiguration

Alle Konstanten (URLs, Pfade, Concurrency, Top-N) sind in `config.py` zentralisiert:

```python
CONCURRENCY  = 8       # parallele Browser-Tabs beim Scrapen
PAGE_TIMEOUT = 30_000  # ms pro Seite
TOP_N_SKILLS = 30      # Balken im Diagramm
```
