# ============================================================
# POP-UP Routine — Task Scheduler Installer
#
# Dieses PowerShell-Skript registriert den Wochenlauf im
# Windows Task Scheduler:
#   - Trigger: Jeden Mittwoch, 10:00 Uhr
#   - Aktion:  pop-up-routine\run_weekly.bat
#   - Bedingung: nur wenn der User eingeloggt ist
#   - Verhalten: Task wird nachgeholt, falls Rechner zur Zeit aus war
#
# Verwendung (in PowerShell, normalem User-Kontext):
#   cd "C:\Users\ma1157761\OneDrive - FHNW\Dokumente\Claude Directory\pop-up-routine"
#   powershell -ExecutionPolicy Bypass -File install_task.ps1
# ============================================================

$TaskName    = "POP-UP Routine FHNW Events"
$ProjectDir  = $PSScriptRoot
$BatchFile   = Join-Path $ProjectDir "run_weekly.bat"

if (-not (Test-Path $BatchFile)) {
    Write-Error "run_weekly.bat nicht gefunden in $ProjectDir"
    exit 1
}

Write-Host "[*] Installiere Task: $TaskName"
Write-Host "    -> Skript: $BatchFile"
Write-Host "    -> Trigger: Jeden Mittwoch 10:00"

# Falls der Task schon existiert: erst entfernen
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "[*] Existierenden Task entfernen..."
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Aktion: ruft die Batch-Datei auf, mit Working-Directory=Projektordner
$action = New-ScheduledTaskAction `
    -Execute $BatchFile `
    -WorkingDirectory $ProjectDir

# Trigger: jede Woche, Mittwoch 10:00
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Wednesday -At 10:00am

# Settings: Nachholen, falls verpasst; max 30 Min Laufzeit; nicht starten wenn Akku
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -DontStopOnIdleEnd `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries

# Principal: laeuft als aktueller User (kein SYSTEM, damit OneDrive-Pfad funktioniert)
$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Wöchentlicher Scrape, Klassifikation und E-Mail-Versand der FHNW-Veranstaltungen."

Write-Host "[+] Task installiert. Naechster Lauf: Mittwoch 10:00."
Write-Host ""
Write-Host "Manuelles Testen:"
Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
Write-Host ""
Write-Host "Status anzeigen:"
Write-Host "  Get-ScheduledTask -TaskName '$TaskName' | Get-ScheduledTaskInfo"
Write-Host ""
Write-Host "Deinstallieren:"
Write-Host "  Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
