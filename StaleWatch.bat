@echo off
rem Usage: StaleWatch.bat ENVIRONMENT [OUTPUT_FOLDER]
rem   Arg 1 (mandatory): the environment, one of PRD PPR ITG QA1 QA2 QA3.
rem   Arg 2 (optional):  folder for the output files (log + state). Defaults to
rem                      the "output_files" folder next to StaleWatch.py.
rem StaleWatch.py is expected to sit in the same folder as this batch file.

rem %~dp0 is this batch file's own folder (with a trailing backslash).
set "SCRIPT_DIR=%~dp0"

if "%~1"=="" (
    echo ERROR: Missing environment argument.
    echo Usage: StaleWatch.bat ENVIRONMENT [OUTPUT_FOLDER]
    echo   ENVIRONMENT must be one of: PRD PPR ITG QA1 QA2 QA3
    exit /b 1
)

if not exist "%SCRIPT_DIR%StaleWatch.py" (
    echo ERROR: StaleWatch.py not found in "%SCRIPT_DIR%"
    exit /b 1
)

if "%~2"=="" (
    echo Running StaleWatch monitor in environment "%~1"...
    python "%SCRIPT_DIR%StaleWatch.py" -e "%~1"
) else (
    echo Running StaleWatch monitor in environment "%~1", output to "%~2"...
    python "%SCRIPT_DIR%StaleWatch.py" -e "%~1" -f "%~2"
)

echo.
echo Process finished.
rem pause
