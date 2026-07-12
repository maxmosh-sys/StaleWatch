@echo off
set "SCRIPT_DIR=%~dp0"

if not exist "%SCRIPT_DIR%stalewatch_test_logger.py" (
    echo ERROR: stalewatch_test_logger.py not found in "%SCRIPT_DIR%"
    exit /b 1
)

echo Running stalewatch_test_logger...
python "%SCRIPT_DIR%stalewatch_test_logger.py" %* %SCRIPT_DIR%test_logger.log 
echo.
echo Process finished.
rem pause
