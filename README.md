# POP-UP Routine

**Created**: 2026-04-30
**Last updated**: 2026-04-30

## Überblick

Wöchentliche automatisierte Überwachung der FHNW-Veranstaltungsseite (https://www.fhnw.ch/de/aktuelles/veranstaltungen/alle).
Die Routine scraped alle gelisteten Events, vergleicht sie mit der Vorwoche und sendet eine kuratierte E-Mail
mit (1) "Claude's Vorschlägen" für hochrelevante Events und (2) einer vollständigen Liste aller neuen Events.

Profil für die Kuration:
- **Format (hart):** Networking & Wissensaustausch zwischen Forschenden, Industrie, Zivilgesellschaft, NGOs, Gemeinden
- **Themen (weich):** Zero Emission, Future Health, New Work

## Architektur

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  scrape.py  │ -> │ diff_events │ -> │ classify.py │ -> │ email_gen.py│ -> │send_email.py│
│ (Playwright)│    │             │    │ (Claude API)│    │   (HTML)    │    │   (SMTP)    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                          ↑
                    baseline.json
                    (letzter Scrape)
```

Orchestrator: `code/run_weekly.py` führt alles in der richtigen Reihenfolge aus.

## Verzeichnisstruktur

| Pfad | Inhalt |
|------|--------|
| `code/scrape.py` | Playwright-Scraper |
| `code/diff_events.py` | Vergleich mit Baseline |
| `code/classify.py` | Klassifikation via Claude API |
| `code/email_gen.py` | HTML-/Text-E-Mail-Generator |
| `code/send_email.py` | SMTP-Versand |
| `code/run_weekly.py` | Orchestrator (Hauptskript) |
| `code/test_api.py` | API-Verbindungstest |
| `data/raw/scrape_<datum>.json` | Roh-Scrape-Archive |
| `data/clean/baseline.json` | Aktuelle Baseline (letzter Scrape) |
| `data/clean/new_events_<datum>.json` | Neue Events der Woche (Diff-Output) |
| `data/clean/classified_<datum>.json` | Klassifizierte neue Events |
| `output/email_<datum>.html` | Generierte HTML-Mail |
| `output/email_<datum>.txt` | Generierte Text-Mail |
| `.env` | Geheime Konfiguration (API-Key, SMTP) — **nicht in Git** |

## Konfiguration

Datei `.env` im Projekt-Root:

```
ANTHROPIC_API_KEY=sk-ant-api03-...

SMTP_SERVER=smtp.office365.com
SMTP_PORT=587
SMTP_USER=vorname.nachname@fhnw.ch
SMTP_PASSWORD=...
SMTP_FROM=vorname.nachname@fhnw.ch
SMTP_TO=vorname.nachname@fhnw.ch,kollegin@fhnw.ch
SMTP_USE_SSL=false
```

## Verwendung

### Erstmalige Initialisierung der Baseline

```bash
python code/run_weekly.py --init
```
Setzt den heutigen Scrape als Baseline. Keine Mail. Diffs werden ab dem nächsten Lauf gegen diese Baseline berechnet.

### Wochenlauf

```bash
python code/run_weekly.py
```
Führt scrape -> diff -> classify -> email_gen -> send_email aus. Bei 0 neuen Events: keine Mail, Baseline wird trotzdem aktualisiert.

### Lauf ohne Versand (zum Testen)

```bash
python code/run_weekly.py --no-send
```
Generiert die Mail unter `output/`, versendet aber nicht.

### Einzelne Bausteine manuell

```bash
python code/scrape.py
python code/classify.py data/raw/scrape_<datum>.json data/clean/classified_<datum>.json
python code/email_gen.py data/clean/classified_<datum>.json output
python code/send_email.py output/email_<datum>.html output/email_<datum>.txt
```

## Trigger / Scheduling

- Wochenlauf: **jeden Mittwoch um 10:00 Uhr** (Windows Task Scheduler)
- Empfänger: `david.dauwalder@fhnw.ch`, `roberto.vadrucci@fhnw.ch`
- Versand-Account: `claudeforschungssupport@gmail.com` (separater Wegwerf-Gmail)

### Task Scheduler einrichten (einmalig)

PowerShell im Projektordner öffnen, dann:

```powershell
powershell -ExecutionPolicy Bypass -File install_task.ps1
```

Damit wird der Task `POP-UP Routine FHNW Events` registriert. Manuelles Testen:

```powershell
Start-ScheduledTask -TaskName 'POP-UP Routine FHNW Events'
```

Status / Logs:
- Task-Status: `Get-ScheduledTask -TaskName 'POP-UP Routine FHNW Events' | Get-ScheduledTaskInfo`
- Lauf-Logs: `output\run_YYYYMMDD.log` (eine Datei pro Lauf)

## Status

- [x] Projekt initialisiert
- [x] Probescrape erfolgreich (86 Events erfasst)
- [x] API-Verbindung getestet
- [x] Klassifikator implementiert (Sonnet 4.6, Schwelle 55)
- [x] Backtest erfolgreich
- [x] Diff-Logik implementiert
- [x] HTML-Mail-Generator implementiert (mit Sicherheitshinweis + URL-Transparenz)
- [x] SMTP-Versand implementiert
- [x] Orchestrator implementiert
- [x] Baseline initialisiert (Stand 2026-04-30)
- [x] SMTP-Konfiguration gesetzt (Gmail-Wegwerf-Account)
- [x] Test-Versand erfolgreich
- [x] Empfänger: David Dauwalder + Roberto Vadrucci
- [x] Datums-Sortierung in der Mail (aufsteigend)
- [x] Task Scheduler Installer (`install_task.ps1`) vorhanden
- [ ] **Du:** `install_task.ps1` einmal ausführen, um den Task zu registrieren
