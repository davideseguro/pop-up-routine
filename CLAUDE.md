# Project Context: POP-UP Routine

> This file is read by Claude at the start of every session. Keep it updated.
> For day-to-day session notes, see `progress_logs/`.

## Was ist dieses Projekt

Eine wöchentliche, vollautomatische Routine, die jeden **Mittwoch um 10:00 Uhr**:

1. Die FHNW-Veranstaltungsseite scraped (Playwright, Headless-Chromium)
2. Die neu hinzugekommenen Events durch Diff gegen die letzte Baseline erkennt
3. Diese Events via Claude API (Sonnet 4.6) gegen ein Profil klassifiziert
4. Eine HTML-E-Mail mit zwei Blöcken generiert ("Claude's Vorschläge" und "Alle neuen Events")
5. Diese Mail per SMTP (Gmail-Wegwerf-Account) an mehrere FHNW-Empfänger versendet

Ziel: Niemand soll mehr eine relevante Networking-Veranstaltung der FHNW verpassen,
ohne aktiv suchen zu müssen.

## Datenquelle

- **URL**: https://www.fhnw.ch/de/aktuelles/veranstaltungen/alle
- **Scraping-Tool**: Playwright (Python), die Seite ist JS-gerendert
- **Felder pro Event**: Name, Datum, Ort, vollständiger Detail-URL
- **Event-ID** für den Diff: vollständiger Detail-URL (eindeutig und stabil)

## Pipeline (Datenfluss)

```
scrape.py (Playwright)
  -> data/raw/scrape_<datum>.json
diff_events.py
  -> data/clean/new_events_<datum>.json   (Diff gegen baseline.json)
classify.py (Claude API: Sonnet 4.6)
  -> data/clean/classified_<datum>.json   (mit match_score, reason, is_recommendation, is_series)
email_gen.py
  -> output/email_<datum>.html / .txt
send_email.py (SMTP)
  -> Versand an SMTP_TO Empfaenger
run_weekly.py orchestriert die obige Kette und ueberschreibt
  data/clean/baseline.json mit dem aktuellen Scrape am Schluss.
```

## Profil für die Klassifikation

**Hartes Kriterium (Format):**
- Networking & Wissensaustausch zwischen verschiedenen Akteuren:
  Forschende, Industrie, Zivilgesellschaft, NGOs, Gemeinden, Verwaltung

**Weiches Kriterium (Themen, bevorzugt):**
- Zero Emission / Nachhaltigkeit / Kreislaufwirtschaft
- Future Health / Medizintechnik / Digital Health
- New Work / Arbeitswelt / Leadership / Lernen

**Schwelle:** match_score >= 55 (Sonnet vergibt typisch 52, 62, 72, 82, 92).

## Konfiguration

`.env` im Projekt-Root (NICHT in Git, durch `.gitignore` geschützt):

| Variable | Wert |
|---|---|
| `ANTHROPIC_API_KEY` | API-Key von console.anthropic.com (Spend-Limit: $5) |
| `SMTP_SERVER` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | `claudeforschungssupport@gmail.com` (Wegwerf-Account) |
| `SMTP_PASSWORD` | Google App-Passwort (16 Zeichen) |
| `SMTP_FROM` | `claudeforschungssupport@gmail.com` |
| `SMTP_TO` | `david.dauwalder@fhnw.ch,roberto.vadrucci@fhnw.ch` |
| `SMTP_USE_SSL` | `false` (STARTTLS auf Port 587) |

## Sicherheits-Eigenschaften

- API-Key durch Spend-Limit ($5) begrenzt → max. dieser Schaden bei Leak
- SMTP läuft über separaten Gmail-Wegwerf-Account → bei Leak nur Spam von dieser einen Adresse möglich, FHNW-Account nicht betroffen
- Mail enthält **immer** einen Sicherheitshinweis am Anfang, der erklärt:
  Mail ist KI-generiert, alle URLs werden als sichtbare Strings angezeigt,
  niemals einen Link anklicken, dessen Linktext nicht der URL entspricht.
- Linktext = vollständige URL überall in der Mail (kein Spoofing möglich)

## Aktueller Status

- Gesamte Pipeline implementiert und manuell getestet
- Test-Versand an david.dauwalder@fhnw.ch erfolgreich
- Baseline mit dem 2026-04-30-Scrape (86 Events) initialisiert
- Task Scheduler: Setup-Skript `install_task.ps1` vorhanden, einmalig vom User auszuführen

## Wichtige Design-Entscheidungen

- **Modell:** Sonnet 4.6 (nicht Opus). Klassifikation ist eine simple Aufgabe,
  Sonnet ist 3× billiger und konsistenter (vergibt diskrete Scores 52/62/72/82/92).
- **Sortierung in der Mail:** Nach Datum AUFSTEIGEND (frueheste Events zuerst).
  NICHT nach Score. Score ist nur Filter für Block 1.
- **Event-ID = URL:** stabiler als der Name (Names koennen Untertitel/Datum bekommen).
- **Diff asymmetrisch:** nur `current \ baseline`. Verschwundene Events ignoriert.
- **Baseline-Update am Schluss:** Aktueller Scrape wird zur neuen Baseline,
  egal ob neue Events da waren oder nicht. Damit verschwundene Events nicht
  in der Folgewoche doch wieder als "neu" gemeldet werden.

## Conventions

- Raw scrapes in `data/raw/scrape_<YYYY-MM-DD>.json` (timestamped, nie überschreiben)
- `data/clean/baseline.json` ist die einzige Wahrheitsquelle für "bereits gesehen"
- Scripts laufen vom Projekt-Root
- Progress logs in `progress_logs/log_<YYYY-MM-DD>_sessionN.md`
- Logs der wöchentlichen Läufe: `output/run_<YYYYMMDD>.log` (vom `run_weekly.bat` geschrieben)

## Was Claude beim nächsten Mal wissen sollte

- Wenn der Nutzer fragt "warum kommen Events nochmal in der Mail" → Baseline checken,
  sie wird nur am Ende eines erfolgreichen Laufs aktualisiert; bei Skript-Crash bleibt sie alt.
- Wenn FHNW die Seitenstruktur ändert → `scrape.py` muss angepasst werden.
  Der Selektor "alle Anchors mit `/veranstaltungen/` im href" ist robust, aber nicht ewig haltbar.
- Falls Klassifikation schlecht trifft → `PROFILE_PROMPT` in `classify.py` anpassen.
  Schwelle ist 55, Sonnet vergibt diskrete Werte → 50/55/60 sind aequivalent (bracket: alle ≥52),
  65/70 sind aequivalent (alle ≥72).
- Datumsformat im Scrape: `D.M.YYYY` (Schweizer Format, ohne führende Nullen).
  `email_gen.parse_date_for_sort()` parst das.

## Pfannenfertige Vorlage für andere Newsletter

Die Pipeline (Scrape → Diff → Classify → HTML-Mail → SMTP-Versand) ist generisch.
Fuer einen neuen Newsletter (andere Quelle, anderes Profil):

1. **`scrape.py`** anpassen: URL und ggf. Selektoren tauschen.
2. **`PROFILE_PROMPT`** in `classify.py` neu formulieren.
3. **`SECURITY_BANNER_TEXT`** und HTML-Header in `email_gen.py` ggf. anpassen
   (insbes. Absender-Adresse im Sicherheitshinweis).
4. **`baseline.json`** loeschen, `python code/run_weekly.py --init` ausfuehren.
5. **`SMTP_TO`** in `.env` setzen.
6. **Task Scheduler**: `install_task.ps1` Trigger-Tag/Zeit anpassen.

Diff-, Mail-Generator-, Versand- und Orchestrator-Logik bleiben unveraendert.
