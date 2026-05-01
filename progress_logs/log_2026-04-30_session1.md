# Progress Log — POP-UP Routine
**Date**: 2026-04-30
**Session**: 1

## What happened this session

- Projekt mit Skill `newproject` initialisiert
- Standard-Verzeichnisstruktur angelegt
- README.md und CLAUDE.md mit Profil und Methodik gefüllt
- Klärung der offenen Punkte mit Nutzer (Scrape via Playwright/Python, neuer Unterordner)

## Current state of the project

Gerüst steht. Noch kein Code, keine Daten. Probescrape ist der nächste Schritt.

## Decisions made

- Scrape-Tool: **Playwright (Python)** — FHNW-Seite ist vermutlich JS-rendered
- Speicherort: **`pop-up-routine/`** im "Claude Directory"
- Event-ID = vollständige Detail-URL
- Felder pro Event: Name, Datum, Ort, Link

## Open questions

- E-Mail-Versand-Methode (SMTP / Resend / andere)
- Scheduling-Mechanismus (Windows Task Scheduler / Claude `schedule` Skill / GitHub Actions)
- Datumsformat (ISO 8601 vs. Roh-String)
- Ist Playwright bereits auf dem System installiert? (`pip install playwright` + `playwright install chromium` ggf. nötig)

## Next steps

1. Prüfen ob Python und Playwright verfügbar sind, ggf. installieren
2. `code/scrape.py` schreiben — initialer Probescrape mit allen Events (Name, Datum, Ort, Link)
3. Output als `data/raw/scrape_2026-04-30.json` speichern
4. Mit Nutzer Resultat reviewen, Datenqualität prüfen, Klassifikation auf Beispiel-Events testen
5. Falls OK: Baseline-Datei erzeugen und über E-Mail-Versand & Scheduling entscheiden

## Files created or modified this session

- README.md (created)
- CLAUDE.md (created)
- progress_logs/log_2026-04-30_session1.md (this file)
