@echo off
REM ==============================================================================
REM GDR-AI Smart Git Pusher (Windows)
REM ==============================================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo ==================================================================
echo GDR-AI Smart Git Pusher (Windows)
echo ==================================================================
echo.

set /p COMMIT_MSG="Enter commit message: "
if "%COMMIT_MSG%"=="" set COMMIT_MSG=chore: update GDR-AI

echo.
echo [*] Staging files...
git add .

REM Safety Check: Verify private/sensitive files are NOT staged
for /f "tokens=*" %%F in ('git diff --cached --name-only ^| findstr /i "\.secrets\.env$ \.env$ gdr_history\.csv gdr_history\.jsonl requests\.db \.backup"') do (
    echo [!] CRITICAL SAFETY STOP: Sensitive file staged: %%F
    echo Aborting push to prevent sensitive credential leaks.
    git reset
    pause
    exit /b 1
)

echo [*] Committing...
git commit -m "%COMMIT_MSG%"

echo.
echo [*] Pushing to origin main...
git push origin main
if errorlevel 1 (
    echo.
    echo [!] Standard push failed. Please enter your credentials:
    set /p GH_USER="GitHub Username [404adarsh]: "
    if "!GH_USER!"=="" set GH_USER=404adarsh
    set /p GH_TOKEN="GitHub Personal Access Token: "
    git push "https://!GH_USER!:!GH_TOKEN!@github.com/404adarsh/GDR-AI.git" main
)

echo.
echo ==================================================================
echo [OK] Done!
echo ==================================================================
pause

