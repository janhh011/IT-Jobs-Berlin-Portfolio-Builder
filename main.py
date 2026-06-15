"""
main.py — CLI-Einstiegspunkt für die get-in-IT Job Scraper Pipeline.

Nutzung:
    python main.py --scrape       # Rohdaten scrapen
    python main.py --enrich       # Skills aus Beschreibungen extrahieren
    python main.py --visualize    # Diagramm erstellen
    python main.py --all          # Alle drei Schritte in Sequenz
"""

import argparse
import asyncio
import logging
import sys

import config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="main.py",
        description="get-in-IT Berlin Job Scraper Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Beispiele:\n"
            "  python main.py --all                  # komplette Pipeline\n"
            "  python main.py --scrape               # nur scrapen\n"
            "  python main.py --enrich --visualize   # anreichern + Diagramm\n"
        ),
    )
    parser.add_argument("--scrape",    action="store_true", help="Scrape Rohdaten von get-in-it.de")
    parser.add_argument("--enrich",    action="store_true", help="Hard Skills aus Beschreibungen extrahieren")
    parser.add_argument("--visualize", action="store_true", help="Top-Skills-Diagramm erstellen")
    parser.add_argument("--all",       action="store_true", help="Alle drei Schritte ausführen")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not any([args.scrape, args.enrich, args.visualize, args.all]):
        parser.print_help()
        sys.exit(1)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )
    log = logging.getLogger("pipeline")

    # Ensure output directories exist
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    do_scrape    = args.scrape    or args.all
    do_enrich    = args.enrich    or args.all
    do_visualize = args.visualize or args.all

    if do_scrape:
        log.info("━━━ STEP 1: SCRAPE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        from scraper import run as scrape_run
        asyncio.run(scrape_run())

    if do_enrich:
        log.info("━━━ STEP 2: ENRICH ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        if not config.RAW_CSV.exists():
            log.error("Raw CSV nicht gefunden: %s — bitte zuerst --scrape ausführen.", config.RAW_CSV)
            sys.exit(1)
        from extract_skills import run as enrich_run
        enrich_run()

    if do_visualize:
        log.info("━━━ STEP 3: VISUALIZE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        if not config.ENRICHED_CSV.exists():
            log.error("Enriched CSV nicht gefunden: %s — bitte zuerst --enrich ausführen.", config.ENRICHED_CSV)
            sys.exit(1)
        from visualize_skills import run as visualize_run
        visualize_run()

    log.info("━━━ Pipeline abgeschlossen ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


if __name__ == "__main__":
    main()
