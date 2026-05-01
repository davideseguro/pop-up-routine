"""
FHNW-Veranstaltungs-Scraper.

Liest alle Events von https://www.fhnw.ch/de/aktuelles/veranstaltungen/alle
und speichert sie als JSON (Name, Datum, Ort, Link).

Verwendung:
    python scrape.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

URL = "https://www.fhnw.ch/de/aktuelles/veranstaltungen/alle"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"


def scrape_events(headless: bool = True) -> list[dict]:
    """Scrape all event tiles from the FHNW events listing page."""
    events: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            locale="de-CH",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        print(f"[*] Navigating to {URL}", file=sys.stderr)
        page.goto(URL, wait_until="domcontentloaded", timeout=60_000)

        # Cookie-Banner: best effort
        try:
            page.wait_for_selector("button:has-text('Akzeptieren')", timeout=3000)
            page.click("button:has-text('Akzeptieren')")
            print("[*] Cookie banner accepted", file=sys.stderr)
        except PlaywrightTimeout:
            pass

        # Wait for event cards to render
        page.wait_for_load_state("networkidle", timeout=30_000)

        # "Mehr laden" / Load-more click loop
        load_more_selectors = [
            "button:has-text('Mehr')",
            "button:has-text('mehr laden')",
            "button:has-text('Weitere')",
            "a:has-text('Mehr anzeigen')",
        ]
        for _ in range(50):  # safety cap
            clicked = False
            for sel in load_more_selectors:
                try:
                    btn = page.query_selector(sel)
                    if btn and btn.is_visible():
                        btn.click()
                        page.wait_for_load_state("networkidle", timeout=15_000)
                        clicked = True
                        break
                except Exception:
                    continue
            if not clicked:
                break

        # Scroll to bottom to trigger any lazy loading
        prev_height = 0
        for _ in range(20):
            curr_height = page.evaluate("document.body.scrollHeight")
            if curr_height == prev_height:
                break
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(800)
            prev_height = curr_height

        # Extract event data — try multiple selector strategies
        # Strategy 1: look for article/card containers with a heading + date
        events_data = page.evaluate(
            """
            () => {
              // Collect anchors that look like event detail links
              const anchors = Array.from(document.querySelectorAll('a'));
              const seen = new Set();
              const results = [];

              for (const a of anchors) {
                const href = a.href || '';
                if (!href.includes('/veranstaltungen/')) continue;
                if (href.endsWith('/veranstaltungen/alle')) continue;
                if (href.endsWith('/veranstaltungen/')) continue;
                if (seen.has(href)) continue;

                // Find the closest container that likely represents the card
                let container = a.closest('article, li, div[class*="teaser"], div[class*="card"], div[class*="event"]') || a;
                const text = (container.innerText || '').trim();
                if (!text) continue;

                // Heuristic: the link text or a heading inside
                const heading = container.querySelector('h1, h2, h3, h4, h5, .title, [class*="title"], [class*="Title"]');
                const name = (heading ? heading.innerText : a.innerText || '').trim();
                if (!name || name.length < 3) continue;

                seen.add(href);
                results.push({
                  name,
                  href,
                  rawText: text,
                });
              }
              return results;
            }
            """
        )

        for ev in events_data:
            events.append(
                {
                    "name": ev.get("name", "").strip(),
                    "url": ev.get("href", "").strip(),
                    "raw_text": ev.get("rawText", "").strip(),
                    # date and location to be parsed in a separate pass
                    "date": "",
                    "location": "",
                }
            )

        browser.close()

    return events


def parse_date_and_location(raw_text: str) -> tuple[str, str]:
    """Best-effort parsing of date and location from a card's raw text."""
    import re

    # Date patterns: "01.05.2026", "1. Mai 2026", "01.05. - 02.05.2026"
    date_match = re.search(
        r"(\d{1,2}\.\d{1,2}\.(?:\d{4}|\d{2})?(?:\s*-\s*\d{1,2}\.\d{1,2}\.\d{2,4})?)",
        raw_text,
    )
    if not date_match:
        date_match = re.search(
            r"(\d{1,2}\.\s*(?:Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s*\d{4})",
            raw_text,
        )
    date_str = date_match.group(1).strip() if date_match else ""

    # Location: heuristic — line that contains a known FHNW campus city or "Online"
    locations = [
        "Brugg-Windisch", "Brugg", "Windisch", "Olten", "Muttenz",
        "Basel", "Solothurn", "Aarau", "Online", "Zürich", "Bern",
    ]
    location = ""
    for loc in locations:
        if loc.lower() in raw_text.lower():
            location = loc
            break
    return date_str, location


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    out_path = RAW_DIR / f"scrape_{today}.json"

    events = scrape_events(headless=True)

    # Post-process: parse date and location from raw_text
    for ev in events:
        d, loc = parse_date_and_location(ev.get("raw_text", ""))
        ev["date"] = d
        ev["location"] = loc

    payload = {
        "scraped_at": today,
        "source_url": URL,
        "count": len(events),
        "events": events,
    }
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[+] Wrote {len(events)} events to {out_path}", file=sys.stderr)

    # Print a short summary to stdout
    for ev in events[:10]:
        print(f"- {ev['name']} | {ev['date']} | {ev['location']} | {ev['url']}")
    if len(events) > 10:
        print(f"... ({len(events) - 10} more)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
