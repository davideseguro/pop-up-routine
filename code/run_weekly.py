"""
POP-UP Routine — Wochenlauf-Orchestrator.

Workflow:
  1. Scrape die FHNW-Veranstaltungsseite (Playwright)
  2. Diff gegen baseline.json
  3. Falls 0 neue Events: nichts machen, Baseline trotzdem updaten, ENDE
  4. Falls >=1 neue Events:
     a. Klassifiziere die neuen Events (Claude API)
     b. Generiere HTML- und Text-E-Mail
     c. (Optional) Versende Mail per SMTP
  5. Aktuellen Scrape als neue baseline.json speichern

Verwendung:
    python run_weekly.py [--no-send]
    python run_weekly.py --init     # initiale Baseline erstellen, KEINE Mail
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import traceback
from datetime import date
from pathlib import Path

# Lokale Module
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "code"))

from scrape import scrape_events, parse_date_and_location, URL as SCRAPE_URL  # noqa: E402
from diff_events import diff  # noqa: E402
from classify import classify_file, MODEL, RECOMMENDATION_THRESHOLD  # noqa: E402
from email_gen import generate_email  # noqa: E402

RAW_DIR = PROJECT_ROOT / "data" / "raw"
CLEAN_DIR = PROJECT_ROOT / "data" / "clean"
OUTPUT_DIR = PROJECT_ROOT / "output"
BASELINE_PATH = CLEAN_DIR / "baseline.json"


def do_scrape() -> Path:
    """Fuehrt einen Scrape aus und schreibt Roh-JSON. Gibt den Pfad zurueck."""
    today = date.today().isoformat()
    out_path = RAW_DIR / f"scrape_{today}.json"
    print(f"[1/5] Scrape FHNW-Seite -> {out_path.name}", file=sys.stderr)

    events = scrape_events(headless=True)
    for ev in events:
        d, loc = parse_date_and_location(ev.get("raw_text", ""))
        ev["date"] = d
        ev["location"] = loc

    payload = {
        "scraped_at": today,
        "source_url": SCRAPE_URL,
        "count": len(events),
        "events": events,
    }
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"      -> {len(events)} Events gefunden", file=sys.stderr)
    return out_path


def do_diff(current_path: Path) -> Path:
    """Diff gegen baseline.json. Gibt Pfad zur new_events.json zurueck."""
    today = date.today().isoformat()
    new_path = CLEAN_DIR / f"new_events_{today}.json"
    print(f"[2/5] Diff gegen baseline -> {new_path.name}", file=sys.stderr)
    diff(BASELINE_PATH, current_path, new_path)
    return new_path


def do_classify(new_events_path: Path) -> Path:
    """Klassifiziert nur die neuen Events. Gibt Pfad zur classified.json zurueck."""
    today = date.today().isoformat()
    classified_path = CLEAN_DIR / f"classified_{today}.json"
    print(f"[3/5] Klassifiziere neue Events -> {classified_path.name}", file=sys.stderr)
    classify_file(new_events_path, classified_path)
    return classified_path


def do_email(classified_path: Path) -> tuple[Path, Path]:
    print(f"[4/5] Generiere HTML/Text-Mail", file=sys.stderr)
    return generate_email(classified_path, OUTPUT_DIR, model=MODEL, threshold=RECOMMENDATION_THRESHOLD)


def do_send(html_path: Path, text_path: Path) -> bool:
    """Optional: SMTP-Versand. Gibt True zurueck, wenn versendet."""
    print(f"[5/5] SMTP-Versand", file=sys.stderr)
    try:
        from send_email import send_mail  # noqa: WPS433
    except ImportError:
        print("      -> send_email.py noch nicht implementiert. Mail liegt in output/.", file=sys.stderr)
        return False
    return send_mail(html_path, text_path)


def update_baseline(current_path: Path) -> None:
    """Aktuellen Scrape als neue Baseline speichern."""
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy(current_path, BASELINE_PATH)
    print(f"[+] Baseline aktualisiert -> {BASELINE_PATH.name}", file=sys.stderr)


def run(*, init: bool = False, no_send: bool = False) -> int:
    try:
        # 1. Scrape
        current_path = do_scrape()

        if init:
            print("[INIT-Modus] Setze aktuellen Scrape als initiale Baseline. Keine Mail.", file=sys.stderr)
            update_baseline(current_path)
            print("[+] Initialisierung fertig. Naechste Woche werden Diffs gegen diese Baseline berechnet.", file=sys.stderr)
            return 0

        if not BASELINE_PATH.exists():
            print(
                "[FEHLER] Keine Baseline vorhanden. Bitte einmalig 'python run_weekly.py --init' ausfuehren.",
                file=sys.stderr,
            )
            return 1

        # 2. Diff
        new_events_path = do_diff(current_path)
        new_count = json.loads(new_events_path.read_text(encoding="utf-8")).get("new_count", 0)

        if new_count == 0:
            print("[+] Keine neuen Events. Baseline wird trotzdem aktualisiert.", file=sys.stderr)
            update_baseline(current_path)
            return 0

        # 3. Klassifizieren
        classified_path = do_classify(new_events_path)

        # 4. E-Mail generieren
        html_path, text_path = do_email(classified_path)

        # 5. Versenden (optional)
        if not no_send:
            do_send(html_path, text_path)
        else:
            print("      -> --no-send aktiv: Mail nicht versendet (liegt in output/)", file=sys.stderr)

        # 6. Baseline updaten (nach erfolgreichem Lauf)
        update_baseline(current_path)
        return 0

    except Exception as exc:  # noqa: BLE001
        print(f"[FEHLER] Workflow abgebrochen: {exc}", file=sys.stderr)
        traceback.print_exc()
        return 2


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="POP-UP Routine: Wochenlauf")
    parser.add_argument("--init", action="store_true", help="Initiale Baseline erstellen (keine Mail)")
    parser.add_argument("--no-send", action="store_true", help="Keine Mail versenden, nur generieren")
    args = parser.parse_args(argv[1:])
    return run(init=args.init, no_send=args.no_send)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
