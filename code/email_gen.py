"""
HTML-E-Mail-Generator fuer die POP-UP Routine.

Liest ein klassifiziertes JSON (mit den NEUEN Events) und generiert eine HTML-Mail
mit zwei Bloecken:
  Block 1: "Claude's Vorschlaege" - Events mit is_recommendation=True
  Block 2: "Alle neuen Events" - alle neuen Events (Tabelle)

WICHTIG (Sicherheit): Alle URLs werden als vollstaendiger sichtbarer Text dargestellt.
Auch wenn sie als <a href> klickbar sind, ist der Link-TEXT immer gleich der URL.
Damit kann der Empfaenger vor jedem Klick pruefen, wohin der Link wirklich zeigt.

Ausgabe: HTML-Datei und Klartext-Datei (multipart-Mail).

Verwendung:
    python email_gen.py <classified_new_events.json> <output_dir>
"""

from __future__ import annotations

import html
import json
import re
import sys
from datetime import date
from pathlib import Path


def parse_date_for_sort(date_str: str) -> tuple[int, int, int]:
    """Parst FHNW-Datumsstrings wie '5.5.2026' oder '01.05. - 02.05.2026'
    in (year, month, day) fuer chronologische Sortierung.
    Wenn nicht parsebar: Tupel mit hohen Zahlen (sortiert ans Ende)."""
    if not date_str:
        return (9999, 99, 99)
    # Erste DD.MM.YYYY-Sequenz extrahieren
    m = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{2,4})", date_str)
    if not m:
        return (9999, 99, 99)
    day = int(m.group(1))
    month = int(m.group(2))
    year_raw = int(m.group(3))
    year = year_raw if year_raw >= 1000 else 2000 + year_raw
    return (year, month, day)


SECURITY_BANNER_TEXT = (
    "Diese E-Mail wurde automatisiert von einer KI erstellt und ueber einen "
    "externen Gmail-Account (claudeforschungssupport@gmail.com) versendet. "
    "Aus Sicherheitsgruenden werden alle Links als vollstaendige URLs dargestellt "
    "und nicht hinter Linktexten verborgen. "
    "Bitte pruefe jede URL vor dem Klick. "
    "Oeffne niemals einen Link aus dieser Mail, der hinter einem Linktext "
    "versteckt ist - das waere ein Anzeichen fuer Manipulation."
)


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<title>POP-UP Routine — {scrape_date}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
         max-width: 720px; margin: 0 auto; padding: 24px; color: #222; line-height: 1.5; }}
  h1 {{ font-size: 22px; border-bottom: 2px solid #c8102e; padding-bottom: 8px; }}
  h2 {{ font-size: 18px; color: #c8102e; margin-top: 32px; border-bottom: 1px solid #ccc; padding-bottom: 4px; }}
  h3 {{ font-size: 15px; color: #555; margin-top: 24px; margin-bottom: 8px; }}
  .meta {{ color: #777; font-size: 13px; margin-bottom: 24px; }}
  .security {{ background: #fff8e1; border: 1px solid #f0c060; border-left: 4px solid #d97706;
               padding: 12px 16px; margin: 16px 0 24px 0; border-radius: 4px;
               font-size: 13px; line-height: 1.55; color: #4a3000; }}
  .security strong {{ color: #6b3000; }}
  .event {{ border-left: 3px solid #c8102e; padding: 10px 14px; margin: 14px 0; background: #fafafa; }}
  .event-title {{ font-weight: 600; font-size: 15px; }}
  .event-meta {{ color: #666; font-size: 13px; margin-top: 4px; }}
  .reason {{ font-style: italic; color: #555; font-size: 13px; margin-top: 6px; }}
  .url-line {{ font-family: Consolas, 'Courier New', monospace; font-size: 12px;
               color: #1a4d8c; margin-top: 8px; word-break: break-all; }}
  .url-line a {{ color: #1a4d8c; text-decoration: underline; }}
  .badge {{ display: inline-block; background: #ffe6cc; color: #884400;
           padding: 1px 6px; border-radius: 3px; font-size: 11px; margin-left: 6px; }}
  .badge-series {{ background: #d6e9ff; color: #1a4d8c; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 13px; margin-top: 12px; }}
  th, td {{ text-align: left; padding: 6px 10px; border-bottom: 1px solid #eee; vertical-align: top; }}
  th {{ background: #f4f4f4; font-weight: 600; }}
  td.url-cell {{ font-family: Consolas, 'Courier New', monospace; font-size: 11px;
                 color: #1a4d8c; word-break: break-all; max-width: 320px; }}
  td.url-cell a {{ color: #1a4d8c; text-decoration: underline; }}
  .footer {{ color: #999; font-size: 12px; margin-top: 40px; border-top: 1px solid #eee; padding-top: 12px; }}
  .empty {{ color: #888; font-style: italic; padding: 12px; background: #fafafa; border-radius: 4px; }}
</style>
</head>
<body>

<h1>POP-UP Routine — Neue FHNW-Veranstaltungen</h1>

<div class="security">
  <strong>🛡️ Sicherheitshinweis:</strong>
  Diese E-Mail wurde automatisiert von einer KI erstellt und über einen externen Gmail-Account
  (<code>claudeforschungssupport@gmail.com</code>) versendet.
  Aus Sicherheitsgründen werden alle Links als vollständige URLs dargestellt und nicht hinter Linktexten verborgen.
  <strong>Bitte prüfe jede URL vor dem Klick.</strong>
  Öffne niemals einen Link aus dieser Mail, der hinter einem Linktext versteckt ist — das wäre ein Anzeichen für Manipulation.
</div>

<div class="meta">Scrape vom {scrape_date} · {new_count} neue Events seit dem letzten Lauf · Quelle:<br>
<span class="url-line"><a href="https://www.fhnw.ch/de/aktuelles/veranstaltungen/alle">https://www.fhnw.ch/de/aktuelles/veranstaltungen/alle</a></span></div>

<h2>🎯 Claude's Vorschläge ({rec_count})</h2>
<div class="meta">Events mit hoher Passgenauigkeit zu deinem Profil (Networking & Wissensaustausch, bevorzugt Zero Emission / Future Health / New Work).</div>
{recommendations_html}

<h2>📋 Alle {new_count} neuen Events</h2>
{all_new_html}

<div class="footer">
  Diese E-Mail wurde automatisch generiert von der POP-UP Routine.<br>
  Klassifikation: Claude {model} · Schwelle: Score ≥ {threshold}
</div>

</body>
</html>
"""


def render_recommendation_block(event: dict) -> str:
    name = html.escape(event.get("name", "").replace("\n", " · "))
    url = event.get("url", "")
    url_escaped = html.escape(url)
    date_str = html.escape(event.get("date", ""))
    location = html.escape(event.get("location", ""))
    reason = html.escape(event.get("reason", ""))
    score = event.get("match_score", 0)
    category = html.escape(event.get("category", ""))
    is_series = event.get("is_series", False)

    badge_series = '<span class="badge badge-series">Eventreihe</span>' if is_series else ""
    meta_parts = [p for p in [date_str, location, category] if p]
    meta = " · ".join(meta_parts)

    # WICHTIG: Linktext = URL (sichtbar, nicht versteckt). a-Tag fuer Klickbarkeit,
    # aber der Inhalt ist die volle URL, sodass kein Spoofing moeglich ist.
    return f"""
<div class="event">
  <div class="event-title">{name} {badge_series}</div>
  <div class="event-meta">{meta} · Score: {score}</div>
  <div class="reason">{reason}</div>
  <div class="url-line">Link: <a href="{url_escaped}">{url_escaped}</a></div>
</div>
"""


def render_table_row(event: dict, index: int) -> str:
    name = html.escape(event.get("name", "").replace("\n", " · "))
    url = event.get("url", "")
    url_escaped = html.escape(url)
    date_str = html.escape(event.get("date", ""))
    location = html.escape(event.get("location", ""))
    star = "★" if event.get("is_recommendation") else ""
    return f"""
<tr>
  <td>{index}</td>
  <td>{star}</td>
  <td>{name}<br><span class="url-line">{url_escaped}</span></td>
  <td>{date_str}</td>
  <td>{location}</td>
</tr>
"""


def generate_email(classified_path: Path, output_dir: Path, model: str = "Sonnet 4.6", threshold: int = 55) -> tuple[Path, Path]:
    payload = json.loads(classified_path.read_text(encoding="utf-8"))
    events = payload.get("events", [])
    scrape_date = payload.get("scraped_at") or payload.get("classified_at") or date.today().isoformat()

    # Alle Events nach Datum aufsteigend sortieren (frueheste zuerst)
    events.sort(key=lambda e: parse_date_for_sort(e.get("date", "")))

    # Empfehlungen ebenfalls nach Datum aufsteigend
    recommendations = [e for e in events if e.get("is_recommendation")]

    if recommendations:
        recommendations_html = "".join(render_recommendation_block(e) for e in recommendations)
    else:
        recommendations_html = '<div class="empty">Keine Events mit hoher Passgenauigkeit in dieser Woche.</div>'

    if events:
        rows = "".join(
            render_table_row(e, i)
            for i, e in enumerate(events, 1)
        )
        all_new_html = f"""
<table>
  <thead>
    <tr><th>#</th><th>★</th><th>Event &amp; URL</th><th>Datum</th><th>Ort</th></tr>
  </thead>
  <tbody>
    {rows}
  </tbody>
</table>
"""
    else:
        all_new_html = '<div class="empty">Keine neuen Events.</div>'

    html_out = HTML_TEMPLATE.format(
        scrape_date=html.escape(scrape_date),
        new_count=len(events),
        rec_count=len(recommendations),
        recommendations_html=recommendations_html,
        all_new_html=all_new_html,
        model=html.escape(model),
        threshold=threshold,
    )

    # Klartext-Version (Fallback) — ebenfalls mit Sicherheitshinweis und vollen URLs
    text_lines = [
        "==============================================================",
        "  POP-UP Routine - Neue FHNW-Veranstaltungen",
        "==============================================================",
        "",
        "[SICHERHEITSHINWEIS]",
        SECURITY_BANNER_TEXT,
        "",
        f"Scrape vom {scrape_date}",
        f"{len(events)} neue Events, davon {len(recommendations)} Vorschlaege",
        "Quelle: https://www.fhnw.ch/de/aktuelles/veranstaltungen/alle",
        "",
        f"=== CLAUDE'S VORSCHLAEGE ({len(recommendations)}) ===",
        "",
    ]
    for e in recommendations:
        name = e.get("name", "").replace("\n", " | ")
        text_lines.append(f"- {name}")
        text_lines.append(f"  Score {e.get('match_score')}: {e.get('reason', '')}")
        meta = " | ".join(filter(None, [e.get("date"), e.get("location"), e.get("category")]))
        if e.get("is_series"):
            meta += " | EVENTREIHE"
        text_lines.append(f"  {meta}")
        text_lines.append(f"  Link: {e.get('url')}")
        text_lines.append("")

    text_lines.append(f"=== ALLE {len(events)} NEUEN EVENTS ===")
    text_lines.append("")
    for i, e in enumerate(events, 1):
        marker = "*" if e.get("is_recommendation") else " "
        name = e.get("name", "").replace("\n", " | ")
        text_lines.append(f"{i:3d}. {marker} {name} | {e.get('date')} | {e.get('location')}")
        text_lines.append(f"      Link: {e.get('url')}")

    text_out = "\n".join(text_lines)

    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = output_dir / f"email_{scrape_date}.html"
    text_path = output_dir / f"email_{scrape_date}.txt"
    html_path.write_text(html_out, encoding="utf-8")
    text_path.write_text(text_out, encoding="utf-8")

    print(f"[+] HTML-Mail: {html_path}", file=sys.stderr)
    print(f"[+] Text-Mail: {text_path}", file=sys.stderr)
    return html_path, text_path


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("Usage: python email_gen.py <classified_new_events.json> <output_dir>", file=sys.stderr)
        return 1
    generate_email(Path(argv[1]), Path(argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
