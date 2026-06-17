@echo off
rem Usage: StaleWatch.bat "C:\path\to\folder-containing-StaleWatch.py"
rem The single argument is the FOLDER that holds StaleWatch.py (path only, no filename).

if "%~1"=="" (
    echo ERROR: Missing argument.
    echo Usage: StaleWatch.bat "C:\path\to\folder-containing-StaleWatch.py"
    exit /b 1
)

if not exist "%~1\StaleWatch.py" (
    echo ERROR: StaleWatch.py not found in "%~1"
    exit /b 1
)

echo Running StaleWatch monitor from "%~1"...
python "%~1\StaleWatch.py"
echo.
echo Process finished.
rem pause
