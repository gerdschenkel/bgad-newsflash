@echo off
REM One click fix for the BGAD News Flash publishing problem.
REM 1. Publishes everything currently sitting in public/ (10, 11 and 12 October).
REM 2. Registers a daily Windows task so this PC does the publishing from now on.
REM Everything it does is written to fix-now.log next to this file.
cd /d "%~dp0"
set LOG=%~dp0fix-now.log
set TASKNAME=BGAD News Flash push

echo ======== %DATE% %TIME% ======== > "%LOG%"
echo STEP 1: publishing the waiting issues >> "%LOG%"

where py >nul 2>nul
if %errorlevel%==0 (
  py tools\publish.py "News Flash 2026-10-12 plus backlog 10 and 11 October" >> "%LOG%" 2>&1
) else (
  python tools\publish.py "News Flash 2026-10-12 plus backlog 10 and 11 October" >> "%LOG%" 2>&1
)
set PUBRC=%errorlevel%
echo STEP 1 exit code: %PUBRC% >> "%LOG%"

echo. >> "%LOG%"
echo STEP 2: registering the daily task >> "%LOG%"
schtasks /create /tn "%TASKNAME%" /tr "\"%~dp0daily-push.bat\"" /sc daily /st 08:15 /f >> "%LOG%" 2>&1
set TASKRC=%errorlevel%
echo STEP 2 exit code: %TASKRC% >> "%LOG%"

if %TASKRC%==0 (
  powershell -NoProfile -Command "$t = Get-ScheduledTask -TaskName '%TASKNAME%'; $t.Settings.StartWhenAvailable = $true; $t.Settings.ExecutionTimeLimit = 'PT30M'; Set-ScheduledTask -InputObject $t | Out-Null" >> "%LOG%" 2>&1
  echo catch up setting applied >> "%LOG%"
)

echo. >> "%LOG%"
echo ALL DONE. publish=%PUBRC% schedule=%TASKRC% >> "%LOG%"
exit /b 0
