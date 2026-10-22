@echo off
REM ==============================================================================
REM GDR-AI One-Click Auto-Repair Script (Windows)
REM ==============================================================================
cd /d "%~dp0"
set "PYTHONPATH=%~dp0;%PYTHONPATH%"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m gdr.repair %*
) else (
    python -m gdr.repair %*
)
pause

