"""
Diff: vergleicht aktuellen Scrape mit Baseline und gibt neue Events zurueck.

Ein Event ist 'neu', wenn seine URL noch nicht in der Baseline vorkommt.

Verwendung:
    python diff_events.py <baseline.json> <current.json> <new_events.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def load_events(path: Path) -> list[dict]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("events", [])


def diff(baseline_path: Path, current_path: Path, output_path: Path) -> dict:
    baseline_events = load_events(baseline_path)
    current_events = load_events(current_path)

    baseline_urls = {e.get("url", "").strip() for e in baseline_events if e.get("url")}

    new_events = []
    for ev in current_events:
        url = ev.get("url", "").strip()
        if not url:
            continue
        if not ev.get("date"):  # Nur echte Events mit Datum
            continue
        if url not in baseline_urls:
            new_events.append(ev)

    payload = json.loads(current_path.read_text(encoding="utf-8"))
    out = {
        "diffed_at": payload.get("scraped_at"),
        "baseline_count": len(baseline_events),
        "current_count": len(current_events),
        "new_count": len(new_events),
        "events": new_events,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"[+] Diff: baseline={len(baseline_events)} current={len(current_events)} "
        f"-> {len(new_events)} neue Events",
        file=sys.stderr,
    )
    print(f"[+] Geschrieben: {output_path}", file=sys.stderr)
    return out


def main(argv: list[str]) -> int:
    if len(argv) < 4:
        print("Usage: python diff_events.py <baseline.json> <current.json> <new_events.json>", file=sys.stderr)
        return 1
    diff(Path(argv[1]), Path(argv[2]), Path(argv[3]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
