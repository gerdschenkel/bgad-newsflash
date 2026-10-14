@echo off
REM One off. Registers a daily Windows task that publishes the BGAD News Flash
REM from this PC, so it no longer depends on the cloud sandbox being allowed to push.
REM Runs at 08:15 local time, and catches up if the PC was asleep.
setlocal
set TASKNAME=BGAD News Flash push

schtasks /create /tn "%TASKNAME%" /tr "\"%~dp0daily-push.bat\"" /sc daily /st 08:15 /f
if errorlevel 1 goto failed

powershell -NoProfile -Command "$t = Get-ScheduledTask -TaskName '%TASKNAME%'; $t.Settings.StartWhenAvailable = $true; $t.Settings.ExecutionTimeLimit = 'PT30M'; Set-ScheduledTask -InputObject $t | Out-Null"

echo.
echo ================================================
echo  DONE. Daily publish task registered.
echo  Name:  %TASKNAME%
echo  Time:  08:15 every day
echo  Log:   %~dp0daily-push.log
echo ================================================
echo.
pause
exit /b 0

:failed
echo.
echo FAILED to register the task. Try running this file as administrator.
echo.
pause
exit /b 1
