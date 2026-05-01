@echo off
REM ============================================================
REM POP-UP Routine — Wochenlauf
REM Diese Datei wird vom Windows Task Scheduler aufgerufen.
REM Mittwochs 10:00 Uhr.
REM ============================================================

cd /d "%~dp0"

REM Logfile mit Datum
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "logdate=%dt:~0,8%"
set "logfile=output\run_%logdate%.log"

echo. >> "%logfile%"
echo ============================================== >> "%logfile%"
echo POP-UP Routine Lauf am %date% %time% >> "%logfile%"
echo ============================================== >> "%logfile%"

python code\run_weekly.py >> "%logfile%" 2>&1

set "exitcode=%errorlevel%"
echo. >> "%logfile%"
echo Lauf beendet mit Exit-Code: %exitcode% >> "%logfile%"

exit /b %exitcode%
