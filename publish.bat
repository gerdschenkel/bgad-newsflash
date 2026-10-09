@echo off
REM Publish the BGAD News Flash. Run this from anywhere, it finds its own folder.
REM Usage:  publish.bat "News Flash 2026-10-08"
cd /d "%~dp0"
set MSG=%~1
if "%MSG%"=="" set MSG=News Flash update

where py >nul 2>nul
if %errorlevel%==0 (
  py tools\publish.py "%MSG%"
) else (
  python tools\publish.py "%MSG%"
)
set RC=%errorlevel%
echo.
if %RC%==0 (echo DONE) else (echo FAILED with exit code %RC%)
pause
