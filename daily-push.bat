@echo off
REM Runs daily from Windows Task Scheduler. Commits and pushes whatever the
REM BGAD News Flash task wrote into public/, and logs the result next to this file.
cd /d "%~dp0"
for /f %%d in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set D=%%d
echo ======== %DATE% %TIME% ========>> "%~dp0daily-push.log"
where py >nul 2>nul
if %errorlevel%==0 (
  py tools\publish.py "News Flash %D%" >> "%~dp0daily-push.log" 2>&1
) else (
  python tools\publish.py "News Flash %D%" >> "%~dp0daily-push.log" 2>&1
)
exit /b %errorlevel%
