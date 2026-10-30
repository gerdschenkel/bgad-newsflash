@echo off
REM One off. Re-registers the daily BGAD News Flash publish task so it retries
REM through the day instead of making a single attempt at 08:15.
REM
REM Why: on 30 Oct 2026 the cloud routine could not reach this PC at 07:14, so
REM nothing was on disk when the 08:15 task ran. The files arrived at 10:02 and
REM sat there unpublished. Repeating the attempt closes that gap.
REM
REM Runs at 08:15, then every 2 hours for 12 hours, and catches up after sleep.
REM Safe to repeat: publish.py commits only when there is something new, and
REM otherwise just pushes anything unpushed.
setlocal
set TASKNAME=BGAD News Flash push

schtasks /create /tn "%TASKNAME%" /tr "\"%~dp0daily-push.bat\"" /sc daily /st 08:15 /f
if errorlevel 1 goto failed

powershell -NoProfile -Command ^
  "$t = Get-ScheduledTask -TaskName '%TASKNAME%';" ^
  "$t.Triggers[0].Repetition.Interval = 'PT2H';" ^
  "$t.Triggers[0].Repetition.Duration = 'PT12H';" ^
  "$t.Settings.StartWhenAvailable = $true;" ^
  "$t.Settings.ExecutionTimeLimit = 'PT30M';" ^
  "Set-ScheduledTask -InputObject $t | Out-Null"
if errorlevel 1 goto failed

echo.
echo ================================================
echo  DONE. Daily publish task updated.
echo  Name:   %TASKNAME%
echo  First:  08:15 every day
echo  Then:   every 2 hours, for 12 hours
echo  Log:    %~dp0daily-push.log
echo ================================================
echo.
pause
exit /b 0

:failed
echo.
echo FAILED to update the task. Try running this file as administrator.
echo.
pause
exit /b 1
