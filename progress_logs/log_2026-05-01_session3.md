# Progress Log — POP-UP Routine
**Date**: 2026-05-01
**Session**: 3

## Was diese Session passiert ist

Migration von lokalem Windows Task Scheduler auf **GitHub Actions (Cloud)** für vollständige Autonomie unabhängig vom lokalen Rechner.

### Setup
- GitHub-Account `davideseguro` erstellt (auf privater E-Mail registriert)
- Privates Repo `davideseguro/pop-up-routine` erstellt
- Personal Access Token erstellt (Permissions: Contents R/W, Workflows R/W; Expiration 2026-12-31)
- Lokales `git init`, erster Commit, `git push -u origin main` erfolgreich
- 8 Repository Secrets im GitHub gesetzt (ANTHROPIC_API_KEY, SMTP_*)

### Neue Dateien
- `requirements.txt` — Python-Abhängigkeiten für GitHub Actions Runner
- `.github/workflows/weekly.yml` — Cron-Workflow:
  - 2 Trigger (08:00 und 09:00 UTC, Mittwochs)
  - DST-Guard skippt zur Laufzeit, falls Schweizer Stunde != 10
  - Bei manuellem `workflow_dispatch` immer durchlaufen
  - Steps: Checkout, Setup Python 3.12, pip install, Playwright install, run_weekly.py, git commit baseline+raw+output

### Code-Anpassungen
- `code/classify.py` — Kommentar an `load_dotenv` (in Cloud kein .env, Secrets kommen direkt aus Env-Vars)
- `.gitignore` erweitert um lokale Backtest-Artefakte und `output/run_*.log`

### Erster Cloud-Lauf (manuell ausgeloest via workflow_dispatch)
- Dauer: 50 Sekunden
- Schritte alle gruen
- Scrape: 93 Events gefunden
- Diff gegen baseline.json (94 Events): 0 neue Events
- Korrekt keine Mail versendet
- Bot committed: 3 files changed (baseline.json, scrape_2026-05-01.json, new_events_2026-05-01.json)
- Commit `13314f7` von `pop-up-routine-bot` ist live in main

## Aktueller Zustand

- Routine produktiv in GitHub Actions
- Erster zeitgesteuerter Lauf: Mittwoch 2026-05-06 um 10:00 Schweiz Zeit (08:00 UTC, Sommerzeit)
- Lokaler Task Scheduler war als Plan B vorbereitet (`install_task.ps1`), wurde aber nicht installiert. Datei bleibt im Repo als Fallback falls Cloud mal ausfaellt.

## Wichtige Sicherheits-Eigenschaften

- `.env` mit Secrets liegt nur lokal, durch `.gitignore` geschuetzt
- GitHub Repository Secrets verschluesselt gespeichert
- Anthropic API-Key Spend-Limit: 5 USD/Monat
- Gmail SMTP via Wegwerf-Account `claudeforschungssupport@gmail.com` mit App-Passwort
- E-Mail enthaelt Sicherheitshinweis und alle URLs als sichtbarer Klartext (Linktext = URL)

## Kosten

- Anthropic API: ~1 Cent pro Woche (nur fuer neue Events)
- GitHub Actions: 0 USD (privates Repo, ca. 50 Sek/Woche, weit unter dem 2000-Min/Monat-Gratis-Limit)

## Naechste Schritte / offene Punkte

1. **Mittwoch 2026-05-06**: Erster automatischer Lauf. Pruefen ob Mail bei beiden Empfaengern ankommt.
2. Falls Mail bei roberto.vadrucci@fhnw.ch im Spam landet -> "Kein Spam" markieren.
3. GitHub schickt automatisch Notification-Mail bei rotem Workflow -> dann eingreifen.

## Was Claude beim naechsten Mal wissen sollte

- Wenn der Nutzer fragt "warum ist heute keine Mail gekommen" -> erst pruefen unter
  https://github.com/davideseguro/pop-up-routine/actions ob der Lauf stattgefunden hat
  und ob 0 neue Events oder ein Fehler.
- Wenn FHNW Seitenstruktur aendert -> `scrape.py` anpassen, lokal testen mit `python code/scrape.py`,
  committen und pushen. Naechster Lauf greift automatisch die neue Version.
- Wenn Token am 2026-12-31 ablaeuft, ist das nur fuer lokales Push relevant. GitHub Actions
  nutzt internen `GITHUB_TOKEN`, der niemals ablaeuft. Token nur erneuern falls man wieder
  lokal pushen will.
