@echo off
rem Usage: StaleWatch.bat [--selftest]
rem Runs StaleWatch.py from this batch file's own folder. Each monitoring task's
rem log file and state file are configured per task in StaleWatch.json.

rem %~dp0 is this batch file's own folder (with a trailing backslash).
set "SCRIPT_DIR=%~dp0"

if not exist "%SCRIPT_DIR%StaleWatch.py" (
    echo ERROR: StaleWatch.py not found in "%SCRIPT_DIR%"
    exit /b 1
)

set EMAIL_PASSWORD=sgobaxtynhysxevl
echo Running StaleWatch monitor...
python "%SCRIPT_DIR%StaleWatch.py" %*
echo.
echo Process finished.
rem pause
