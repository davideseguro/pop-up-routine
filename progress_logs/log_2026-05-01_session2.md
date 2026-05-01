# Progress Log — POP-UP Routine
**Date**: 2026-05-01
**Session**: 2

## Was diese Session passiert ist

Die komplette Pipeline wurde gebaut, getestet und produktiv konfiguriert.

### Implementiert
- `code/scrape.py` — Playwright-Scraper für FHNW-Veranstaltungsseite
- `code/diff_events.py` — Diff gegen `data/clean/baseline.json`
- `code/classify.py` — Klassifikation per Claude API (Sonnet 4.6, Schwelle 55)
- `code/email_gen.py` — HTML- + Text-Mail-Generator mit Sicherheitshinweis und voll sichtbaren URLs, sortiert nach Datum aufsteigend
- `code/send_email.py` — SMTP-Versand (multipart/alternative HTML+Text)
- `code/run_weekly.py` — Orchestrator (scrape → diff → classify → mail → send → baseline-update)
- `code/test_api.py` — Verbindungstest für die Anthropic API
- `run_weekly.bat` — Wrapper für den Task Scheduler, schreibt Logs nach `output/run_<datum>.log`
- `install_task.ps1` — PowerShell-Skript zur Registrierung des Wochenlaufs im Task Scheduler

### Konfiguration final
- Anthropic API-Key in `.env`, Spend-Limit in der Console auf $5 gesetzt
- Gmail-Wegwerf-Account `claudeforschungssupport@gmail.com` mit App-Passwort
- 2FA für diesen Gmail-Account aktiviert
- SMTP-Empfänger: `david.dauwalder@fhnw.ch`, `roberto.vadrucci@fhnw.ch`
- Trigger: Mittwochs 10:00 Uhr (im `install_task.ps1` definiert)

### Tests
- API-Verbindungstest erfolgreich ($0.0008 verbraucht)
- Backtest mit Opus 4.6 auf allen 86 Events: gut, aber inkonsistent bei gleichen Reihen ($0.55)
- Backtest mit Sonnet 4.6: konsistenter, diskrete Scores in 10er-Schritten ($0.58 für 86 Events; pro Wochenlauf erwartet < 5¢)
- 3 Test-Mails an david.dauwalder@fhnw.ch versendet (Erste mit altem Layout, zweite mit Sicherheitshinweis + URL-Transparenz, dritte mit chronologischer Sortierung)

### Wichtige Design-Entscheidungen dieser Session
- **Sonnet 4.6 statt Opus 4.6:** 3× billiger, konsistenter, fuer diese Aufgabe ausreichend
- **Schwelle 55:** 43 Vorschlaege von 86 Backtest-Events (mittel, nicht zu eng)
- **URLs immer sichtbar:** Linktext = URL überall, plus gelber Sicherheitshinweis am Mail-Anfang. Ist als Memory-Feedback gespeichert.
- **Sortierung nach Datum aufsteigend:** in BEIDEN Mail-Bloecken
- **Gmail-Wegwerf statt FHNW-SMTP:** sicherheitstechnisch sauberer (Schaden bei Leak des App-Passworts auf den einen Account begrenzt, FHNW-Account unangetastet)

## Aktueller Zustand

- Pipeline komplett funktionsfähig
- Manuelle Läufe getestet und erfolgreich
- `data/clean/baseline.json` enthält den Scrape vom 2026-04-30 (86 Events)
- Versandfähig an beide Empfänger

## Offene Punkte

- **EINMALIG vom Nutzer:** PowerShell im Projektordner öffnen, `install_task.ps1` ausführen, damit der Task Scheduler den Mittwochs-Lauf registriert. Bis dahin läuft die Routine nicht automatisch.
- Falls FHNW die Seitenstruktur ändert: Scraper muss angepasst werden. Aktueller Selektor (Anchors mit `/veranstaltungen/` im href) ist robust aber nicht ewig.
- Keine Tests für den Edge-Case "0 neue Events". Logik ist drin (`new_count == 0` → keine Mail, Baseline trotzdem update), aber nicht durchgespielt.

## Nächste Schritte

1. Nutzer führt `install_task.ps1` einmalig in PowerShell aus
2. Erster automatischer Lauf: Mittwoch 2026-05-06 um 10:00 (= ein Tag plus heute)
3. Nach diesem Lauf: prüfen, ob die Mail bei beiden Empfängern angekommen ist und keine Fehler im `output/run_*.log` stehen

## In dieser Session geänderte oder erstellte Dateien

- README.md (aktualisiert)
- CLAUDE.md (komplett überarbeitet, jetzt mit Pipeline-Diagramm und Vorlagen-Hinweis für künftige Newsletter)
- .env (SMTP-Konfiguration eingefuegt durch Nutzer, dann zweite Empfaengeradresse ergaenzt)
- .gitignore (vorhanden, schützt .env)
- code/scrape.py (neu)
- code/diff_events.py (neu)
- code/classify.py (neu)
- code/email_gen.py (neu, mit Sicherheitshinweis + URL-Transparenz + Datums-Sortierung)
- code/send_email.py (neu)
- code/run_weekly.py (neu)
- code/test_api.py (neu)
- run_weekly.bat (neu, fuer Task Scheduler)
- install_task.ps1 (neu, Task-Scheduler-Installer)
- data/raw/scrape_2026-04-30.json (initialer Scrape, 86 Events)
- data/clean/baseline.json (Kopie des initialen Scrape, ist nun die Baseline)
- data/clean/classified_2026-04-30_*.json (Backtest-Outputs Opus + Sonnet)
- output/email_2026-04-30.html / .txt (zuletzt: mit Datums-Sortierung)
- output/demo_email_2026-04-30.md (manuelle Demo-Mail von Session 1, archivisch)
- progress_logs/log_2026-05-01_session2.md (diese Datei)
