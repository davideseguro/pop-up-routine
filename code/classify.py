"""
Klassifikator fuer FHNW-Events.

Liest ein Scrape-JSON, schickt jedes Event an Claude API, und schreibt
ein klassifiziertes JSON mit:
  - match_score (0-100): Passgenauigkeit zum Profil
  - is_recommendation (bool): true wenn match_score >= SCHWELLE
  - category: thematische Einordnung
  - reason: kurze Begruendung
  - is_series (bool): Teil einer Eventreihe?

Verwendung:
    python classify.py data/raw/scrape_2026-04-30.json data/clean/classified_2026-04-30.json
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import anthropic
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Lokal: .env wird geladen und ueberschreibt leere Env-Vars.
# Cloud (GitHub Actions): .env existiert nicht; Secrets kommen direkt aus Env -
# load_dotenv ist dann ein No-Op.
load_dotenv(PROJECT_ROOT / ".env", override=True)

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
MODEL = "claude-sonnet-4-6"
RECOMMENDATION_THRESHOLD = 55  # ab welchem match_score ein Event als Vorschlag markiert wird

PROFILE_PROMPT = """Du klassifizierst eine FHNW-Veranstaltung fuer einen Forschenden, der gezielt nach
Networking-Events sucht.

PROFIL DES NUTZERS:
- HARTES KRITERIUM (Format): Das Event muss Networking & Informationsaustausch
  zwischen verschiedenen Akteuren ermoeglichen: Forschende, Industrie,
  Zivilgesellschaft, NGOs, Gemeinden, Verwaltung. Reine Studierenden-Events,
  Konzerte, Ausstellungen ohne Diskussionsformat oder rein interne Events
  (z.B. Tag der offenen Tuer fuer zukuenftige Studis) zaehlen NICHT.
- WEICHES KRITERIUM (Themen, bevorzugt aber nicht zwingend):
  Zero Emission / Nachhaltigkeit / Kreislaufwirtschaft, Future Health /
  Medizintechnik / Digital Health, New Work / Arbeitswelt / Leadership /
  Lernen.

BEKANNTE BEISPIEL-TREFFER (zur Kalibrierung):
  - Transfer Transparent
  - Full Circle Symposium
  - Ringvorlesung
  - Forschungsseminar
  - Zero Emission Konkret
  - Roboter Treff / Rover Traeff / Robot Day
  - Netzwelten Bauen
  - Bauphysik Apero
  - Internationale Tagung Soziale Arbeit und Stadtentwicklung

ANWEISUNG:
Bewerte das folgende Event. Gib eine Antwort als JSON-Objekt mit GENAU diesen Feldern:
{
  "match_score": <Integer 0-100, Passgenauigkeit zum Profil>,
  "category": <"Zero Emission" | "Future Health" | "New Work" | "Forschung" |
               "Networking" | "Tagung/Konferenz" | "Robotik/Tech" |
               "Bildung" | "Kunst/Kultur" | "Sonstiges">,
  "reason": <max 1 Satz Begruendung auf Deutsch>,
  "is_series": <true|false>
}

Gib NUR das JSON-Objekt zurueck, ohne Markdown-Codeblock, ohne Erklaerung davor oder danach.

EVENT:
"""


def classify_event(client: anthropic.Anthropic, event: dict) -> dict:
    """Klassifiziert ein einzelnes Event via Claude API."""
    event_text = (
        f"Name: {event.get('name', '').strip()}\n"
        f"Datum: {event.get('date', '').strip()}\n"
        f"Ort: {event.get('location', '').strip()}\n"
        f"URL: {event.get('url', '').strip()}\n"
        f"Roh-Text der Karte: {event.get('raw_text', '')[:500]}"
    )

    msg = client.messages.create(
        model=MODEL,
        max_tokens=400,
        messages=[
            {"role": "user", "content": PROFILE_PROMPT + event_text},
        ],
    )

    # Antwort extrahieren
    response_text = ""
    for block in msg.content:
        if block.type == "text":
            response_text += block.text
    response_text = response_text.strip()

    # Robustes JSON-Parsing (falls doch Markdown-Wrapper)
    if response_text.startswith("```"):
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:].strip()

    try:
        result = json.loads(response_text)
    except json.JSONDecodeError as e:
        print(f"[WARN] JSON-Parse-Fehler fuer '{event.get('name', '')[:50]}': {e}", file=sys.stderr)
        print(f"[WARN] Rohantwort: {response_text[:200]}", file=sys.stderr)
        result = {
            "match_score": 0,
            "category": "Sonstiges",
            "reason": "Klassifikation fehlgeschlagen (JSON-Parse-Fehler).",
            "is_series": False,
        }

    # Vorschlag-Flag basierend auf Schwelle
    result["is_recommendation"] = result.get("match_score", 0) >= RECOMMENDATION_THRESHOLD

    # Token-Verbrauch
    result["_usage"] = {
        "input_tokens": msg.usage.input_tokens,
        "output_tokens": msg.usage.output_tokens,
    }
    return result


def classify_file(input_path: Path, output_path: Path) -> None:
    if not API_KEY:
        print("[FEHLER] ANTHROPIC_API_KEY nicht gesetzt.", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=API_KEY)

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    events = payload.get("events", [])
    # Nur Events mit Datum klassifizieren (gefilterte echte Events)
    real_events = [e for e in events if e.get("date")]
    print(f"[*] Klassifiziere {len(real_events)} Events von {len(events)} total...", file=sys.stderr)

    classified: list[dict] = []
    total_input = 0
    total_output = 0
    start = time.time()

    for i, event in enumerate(real_events, 1):
        result = classify_event(client, event)
        merged = {**event, **{k: v for k, v in result.items() if not k.startswith("_")}}
        classified.append(merged)
        total_input += result["_usage"]["input_tokens"]
        total_output += result["_usage"]["output_tokens"]
        marker = "★" if result["is_recommendation"] else " "
        print(
            f"  [{i:2d}/{len(real_events)}] {marker} score={result['match_score']:3d} "
            f"cat={result['category']:<20} {event['name'][:60]}",
            file=sys.stderr,
        )

    elapsed = time.time() - start
    cost = (total_input * 5 + total_output * 25) / 1_000_000
    print(
        f"\n[+] Fertig in {elapsed:.1f}s. Tokens: input={total_input} output={total_output} "
        f"-> Kosten ca. ${cost:.4f}",
        file=sys.stderr,
    )

    out = {
        "scraped_at": payload.get("scraped_at"),
        "classified_at": time.strftime("%Y-%m-%d"),
        "source_url": payload.get("source_url"),
        "model": MODEL,
        "threshold": RECOMMENDATION_THRESHOLD,
        "count": len(classified),
        "recommendations_count": sum(1 for e in classified if e.get("is_recommendation")),
        "events": classified,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[+] Geschrieben: {output_path}", file=sys.stderr)


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("Usage: python classify.py <input.json> <output.json>", file=sys.stderr)
        return 1
    classify_file(Path(argv[1]), Path(argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
