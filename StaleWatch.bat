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

rem EMAIL_PASSWORD must already be set as a persistent environment variable
rem (run once, from an elevated prompt: setx EMAIL_PASSWORD "your_app_password_here").
rem Do not hardcode the password here - it would get committed to source control.
echo Running StaleWatch monitor...
python "%SCRIPT_DIR%StaleWatch.py" %*
echo.
echo Process finished.
rem pause
