# Progress Log — POP-UP Routine
**Date**: 2026-05-13
**Session**: 5

## Was diese Session passiert ist

Zweite Mittwochs-Auslosung in Folge nicht erfolgt durch GitHubs Cron. Diagnose und Migration auf externen Scheduler.

### Symptom
- Mittwoch 2026-05-13 10:15 Uhr Schweiz: keine Mail eingetroffen
- GitHub Actions: kein scheduled Lauf heute, letzter Cron-Lauf war 2026-05-06 18:12 UTC (10 Std verspaetet, korrekt vom Zeit-Guard geblockt)
- Manueller Lauf 2026-05-06 11:54 lief erfolgreich (mail kam), aber Cron weiter unzuverlaessig

### Diagnose
GitHub Actions Crons sind dokumentiert als "best effort", besonders zu vollen Stunden / Viertelstunden. Bei der ersten Migration auf off-peak Minuten (`:05`, `:15`) auch keine Verbesserung. GitHub priorisiert push-getriggerte Workflows; Cron wird gedroppt wenn Scheduler ueberlastet.

### Loesung: externer Scheduler

1. Workflow auf `repository_dispatch` als PRIMARY-Trigger umgestellt
2. GitHub-Cron-Trigger als Fallback im Workflow belassen
3. **cron-job.org** Account angelegt (gratis-Plan)
4. Zweiten GitHub PAT erstellt mit minimalen Permissions: nur `Contents: Read and write`
5. Cron-Job in cron-job.org konfiguriert:
   - URL: `https://api.github.com/repos/davideseguro/pop-up-routine/dispatches`
   - Method: POST
   - Schedule: Mittwoch 10:00 Schweiz Zeit
   - Body: `{"event_type": "weekly-run"}`
   - Headers: Authorization Bearer + Accept + X-GitHub-Api-Version
6. Test-Trigger ausgeloest -> HTTP 204 von GitHub -> Workflow lief -> zweite Mail empfangen

### Architektur jetzt

```
cron-job.org (Mittwoch 10:00 Schweiz)
  -> POST api.github.com/repos/.../dispatches
  -> Event "weekly-run"
  -> GitHub Actions startet workflow
  -> Scrape -> Diff -> Classify -> Mail -> Commit
```

### Wichtige Erkenntnis
GitHub-Cron ist fuer zeitkritische Routinen ungeeignet. Diese Erkenntnis wurde in der Memory als feedback-Memory hinterlegt UND im Cloud-Routine-Template (SKILL.md + SETUP_GUIDE.md) als Standard-Setup integriert.

## Aktueller Zustand

- POP-UP Routine produktiv mit cron-job.org als Trigger
- GitHub-Cron als Fallback aktiv
- Beide Mails heute empfangen (manueller Trigger + cron-job.org Test)
- Naechster automatischer Lauf: Mittwoch 2026-05-20 10:00 via cron-job.org

## In dieser Session geaenderte oder erstellte Dateien

- pop-up-routine/.github/workflows/weekly.yml (repository_dispatch als Primary, Cron als Fallback)
- templates/cloud-routine-ai-classification/SKILL.md (Hinweis zu unzuverlaessigem GitHub-Cron)
- templates/cloud-routine-ai-classification/SETUP_GUIDE.md (Phase 7b: externer Scheduler-Setup)
- templates/cloud-routine-ai-classification/scaffold/.github/workflows/weekly.yml (synced)
- ~/.claude/.../memory/feedback_github_cron_unreliable.md (neu)
- ~/.claude/.../memory/MEMORY.md (Eintrag hinzugefuegt)
- progress_logs/log_2026-05-13_session5.md (diese Datei)

## Was Claude beim naechsten Mal wissen sollte

- Wenn Nutzer fragt "Routine triggert nicht zuverlaessig": pruefen ob ueberhaupt cron-job.org als Trigger eingestellt ist. Wenn nur GitHub-Cron: DAS ist die Ursache.
- cron-job.org Job-Logs zeigen jede Auslosung. Wenn dort 204 No Content, dann hat GitHub den Trigger akzeptiert. Wenn Workflow trotzdem nicht laeuft: Token-Permission oder Workflow-Trigger-Typ pruefen.
