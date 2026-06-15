import asyncio
import csv
import re
import sys
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

START_URL   = "https://www.get-in-it.de/it-jobs-berlin"
SEARCH_URL  = "https://www.get-in-it.de/jobsuche?city=6176&radius=25"
BASE_URL    = "https://www.get-in-it.de"
OUTPUT_FILE = Path(__file__).parent / "jobs_berlin.csv"
CONCURRENCY = 8
PAGE_TIMEOUT = 30_000  # ms

SKIP_BADGE_TEXTS = {"Tipp", "Neu", "Top"}


# ── helper: accept cookie banner once ───────────────────────────────────────

async def accept_cookies(page):
    try:
        btn = page.locator("button", has_text="Allen Cookies zustimmen")
        if await btn.is_visible(timeout=3_000):
            await btn.click()
            await page.wait_for_timeout(500)
    except Exception:
        pass


# ── Step 1: collect all job URLs via "Mehr anzeigen" ───────────────────────

async def collect_job_urls(browser) -> list[str]:
    page = await browser.new_page()

    # Land on the city page, then follow "Alle anzeigen" to the full search
    await page.goto(START_URL, wait_until="domcontentloaded", timeout=60_000)
    await page.wait_for_timeout(1_500)
    await accept_cookies(page)

    # Navigate to the full search listing for Berlin
    await page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=60_000)
    await page.wait_for_timeout(1_500)

    # Click "Mehr anzeigen" until it's gone
    clicked = 0
    while True:
        await page.wait_for_timeout(700)
        btn = page.locator("button", has_text="Mehr anzeigen").first
        try:
            if await btn.is_visible(timeout=2_000):
                await btn.scroll_into_view_if_needed()
                await btn.click()
                clicked += 1
                print(f"  'Mehr anzeigen' click #{clicked}", flush=True)
            else:
                break
        except PWTimeout:
            break
        except Exception:
            break

    # Collect unique job hrefs
    anchors = await page.locator('a[href*="/jobsuche/p"]').all()
    seen: set[str] = set()
    urls: list[str] = []
    for a in anchors:
        href = await a.get_attribute("href") or ""
        if href and href not in seen:
            seen.add(href)
            urls.append(BASE_URL + href if href.startswith("/") else href)

    await page.close()
    print(f"  collected {len(urls)} job URLs", flush=True)
    return urls


# ── Step 2: scrape one job detail page ──────────────────────────────────────

async def scrape_job(context, url: str, semaphore: asyncio.Semaphore) -> dict | None:
    async with semaphore:
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
            await page.wait_for_timeout(500)
        except Exception as e:
            await page.close()
            return None

        try:
            # ── company name ──────────────────────────────────────────────
            company = ""
            try:
                el = page.locator('[class*="company"]').first
                company = (await el.text_content(timeout=3_000) or "").strip()
            except Exception:
                pass
            if not company:
                try:
                    el = page.locator('[class*="Logo"] img').first
                    company = (await el.get_attribute("alt") or "").strip()
                except Exception:
                    pass
            # page-title fallback: "JobTitle | Company | get in IT"
            if not company:
                m = re.search(r"\|\s*(.+?)\s*\|\s*get in IT", await page.title(), re.I)
                if m:
                    company = m.group(1).strip()

            # ── position name ─────────────────────────────────────────────
            position = ""
            try:
                position = (await page.locator("h1").first.text_content(timeout=3_000) or "").strip()
            except Exception:
                pass

            # ── description: h2/h3 sections with content ──────────────────
            desc_parts: list[str] = []
            try:
                headings = await page.locator("h2, h3").all()
                relevant_kws = ("Aufgaben", "Profil", "Anforderung", "Qualifikation",
                                "Tätigkeitsbereich", "Aufgabenbereich", "Wir suchen",
                                "Du bringst", "Du wirst", "Was du")
                for h in headings:
                    h_text = (await h.text_content() or "").strip()
                    if not any(kw.lower() in h_text.lower() for kw in relevant_kws):
                        continue
                    # grab all text from sibling elements until next heading
                    section_text = await page.evaluate("""(el) => {
                        let parts = [];
                        let sib = el.nextElementSibling;
                        while (sib && !['H1','H2','H3','H4'].includes(sib.tagName)) {
                            const t = sib.innerText || sib.textContent || '';
                            if (t.trim()) parts.push(t.trim());
                            sib = sib.nextElementSibling;
                        }
                        return parts.join(' ');
                    }""", await h.element_handle())
                    if section_text.strip():
                        desc_parts.append(f"{h_text}: {section_text.strip()}")
            except Exception:
                pass

            # broad fallback if nothing found
            if not desc_parts:
                try:
                    for sel in ["main", "article", '[class*="JobContent"]', '[class*="job-content"]']:
                        loc = page.locator(sel).first
                        if await loc.is_visible(timeout=1_000):
                            txt = (await loc.text_content() or "").strip()
                            if len(txt) > 80:
                                desc_parts.append(txt[:2500])
                                break
                except Exception:
                    pass

            description = " | ".join(desc_parts)
            description = re.sub(r"\s+", " ", description).strip()

            # ── skills: badge chips in job header ─────────────────────────
            # Primary: JobHeaderRegular_jobBadge elements (technology tags)
            skill_tags: list[str] = []
            try:
                badges = await page.locator('[class*="jobBadge"], [class*="JobBadge"]').all()
                for b in badges:
                    txt = (await b.text_content() or "").strip()
                    if txt and txt not in SKIP_BADGE_TEXTS:
                        skill_tags.append(txt)
            except Exception:
                pass

            # Secondary: JobInfo section (Berufsfelder, Studienfächer, Abschluss)
            if not skill_tags:
                try:
                    info_rows = await page.locator('[class*="JobInfo_info"]').all()
                    for row in info_rows:
                        txt = (await row.text_content() or "").strip()
                        if txt:
                            # strip label (e.g. "Berufsfelder") and split entries
                            parts = re.split(r"^[A-ZÄÖÜ][a-zäöü]+\s*", txt)
                            for part in parts:
                                for item in re.split(r"[\n,]", part):
                                    item = item.strip()
                                    if item and len(item) < 60:
                                        skill_tags.append(item)
                except Exception:
                    pass

            # Deduplicate, strip noise
            skip_re = re.compile(
                r"^(berlin|münchen|hamburg|köln|frankfurt|vollzeit|teilzeit|"
                r"praktikum|werkstudent|\d{4}|anzeigen|profil|login)$", re.I
            )
            clean_skills: list[str] = []
            for s in skill_tags:
                s = re.sub(r"\s+", " ", s).strip()
                if s and not skip_re.match(s) and s not in clean_skills:
                    clean_skills.append(s)

            return {
                "company_name": company,
                "position_name": position,
                "position_description": description,
                "skills": ";".join(clean_skills),
            }

        except Exception as e:
            print(f"  ERROR {url}: {e}", flush=True)
            return None
        finally:
            await page.close()


# ── Step 3: main ─────────────────────────────────────────────────────────────

async def main():
    print("Step 1 — loading all Berlin IT job listings …", flush=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # Collect URLs from listing page
        job_urls = await collect_job_urls(browser)
        if not job_urls:
            print("No job URLs found — aborting.", file=sys.stderr)
            await browser.close()
            return

        # Create a shared context so cookies carry over to all detail pages
        context = await browser.new_context()
        # Prime cookies by visiting the site once
        priming = await context.new_page()
        await priming.goto(BASE_URL, wait_until="domcontentloaded", timeout=15_000)
        await accept_cookies(priming)
        await priming.close()

        print(f"\nStep 2 — scraping {len(job_urls)} job pages (concurrency={CONCURRENCY}) …", flush=True)
        semaphore = asyncio.Semaphore(CONCURRENCY)
        tasks = [scrape_job(context, url, semaphore) for url in job_urls]

        results: list[dict] = []
        done = 0
        for coro in asyncio.as_completed(tasks):
            row = await coro
            done += 1
            if row:
                results.append(row)
            if done % 100 == 0 or done == len(job_urls):
                print(f"  {done}/{len(job_urls)} pages done, {len(results)} successful", flush=True)

        await context.close()
        await browser.close()

    print(f"\nStep 3 — writing {len(results)} rows …", flush=True)
    fieldnames = ["company_name", "position_name", "position_description", "skills"]
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\nDone. {len(results)} rows → {OUTPUT_FILE}\n")

    # Show first 2 data rows
    print("── First 2 rows (truncated) ───────────────────────────────")
    with open(OUTPUT_FILE, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= 3:
                break
            # truncate long fields for display
            cols = line.rstrip().split(",")
            truncated = [c[:80] + "…" if len(c) > 80 else c for c in cols]
            print(",".join(truncated))


if __name__ == "__main__":
    asyncio.run(main())
