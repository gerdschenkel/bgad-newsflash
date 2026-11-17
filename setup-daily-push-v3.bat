@echo off
REM One off. Re-registers the daily BGAD News Flash publish task so it starts
REM later and retries hourly, instead of firing once before the files exist.
REM
REM Why: the cloud routine writes public/issues/<date>.html and its cover some
REM time between 07:10 and 11:00 Sydney, because the scheduler itself can run
REM hours late. On 16 Nov 2026 the push ran at 09:38, the files landed at 10:08,
REM and that issue sat unpublished for a full day. Starting at 09:00 and
REM repeating every hour closes the gap whenever the routine actually lands.
REM
REM Safe to repeat: publish.py commits only when there is something new, and
REM otherwise just pushes anything unpushed.
setlocal
set TASKNAME=BGAD News Flash push

schtasks /create /tn "%TASKNAME%" /tr "\"%~dp0daily-push.bat\"" /sc daily /st 09:00 /f
if errorlevel 1 goto failed

powershell -NoProfile -Command ^
  "$t = Get-ScheduledTask -TaskName '%TASKNAME%';" ^
  "$t.Triggers[0].Repetition.Interval = 'PT1H';" ^
  "$t.Triggers[0].Repetition.Duration = 'PT14H';" ^
  "$t.Settings.StartWhenAvailable = $true;" ^
  "$t.Settings.ExecutionTimeLimit = 'PT30M';" ^
  "Set-ScheduledTask -InputObject $t | Out-Null"
if errorlevel 1 goto failed

echo.
echo ================================================
echo  DONE. Daily publish task updated.
echo  Name:   %TASKNAME%
echo  First:  09:00 every day
echo  Then:   every hour, for 14 hours
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
