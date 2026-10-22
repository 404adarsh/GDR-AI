@echo off
REM ==============================================================================
REM Aarushi AI / GDR Agent - Quick Launcher (Windows)
REM ==============================================================================
setlocal EnableDelayedExpansion

cd /d "%~dp0"
set "PYTHONPATH=%~dp0;%PYTHONPATH%"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

if not exist ".venv\Scripts\python.exe" (
    echo [!] Virtual environment not found. Running installer first...
    call install.bat
)

if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo [*] Generated default .env file.
    )
)

if "%~1"=="" (
    echo [*] Starting GDR-AI Web Dashboard at http://127.0.0.1:8844 ...
    start http://127.0.0.1:8844
    ".venv\Scripts\python.exe" -m gdr.cli --gui
) else (
    ".venv\Scripts\python.exe" -m gdr.cli %*
)
pause

