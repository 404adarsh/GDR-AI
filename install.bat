@echo off
REM ==============================================================================
REM Aarushi AI / GDR Agent - Universal Windows Installer
REM Automatically configures Python, virtualenv, and dependencies.
REM ==============================================================================
setlocal EnableDelayedExpansion

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo ==================================================================
echo  Aarushi AI / GDR Agent - Windows Installer
echo ==================================================================
echo.

cd /d "%~dp0"

REM ------------------------------------------------------------------------------
REM 1. Find Python 3.11
REM    Try: py -3.11 first (Python Launcher), then check 'python' version
REM ------------------------------------------------------------------------------
set "PY_CMD="

REM Try Python Launcher (py.exe) with explicit 3.11
py -3.11 --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PY_CMD=py -3.11"
    goto :python_found
)

REM Try 'python' and check if it's 3.11+
where python >nul 2>&1
if %errorlevel% equ 0 (
    python -c "import sys; exit(0 if sys.version_info >= (3,11) else 1)" >nul 2>&1
    if !errorlevel! equ 0 (
        set "PY_CMD=python"
        goto :python_found
    )
)

REM Try known Python 3.11 installation path
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    goto :python_found
)

REM Python 3.11 not found - try to install
echo [!] Python 3.11 was not detected. Attempting automated install...
where winget >nul 2>&1
if %errorlevel% equ 0 (
    echo [*] Installing Python 3.11 via winget...
    winget install --id Python.Python.3.11 --exact --accept-package-agreements --accept-source-agreements --silent
    if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
        set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        goto :python_found
    )
)

echo [!] Downloading Python 3.11.9 installer...
powershell -Command "(New-Object System.Net.WebClient).DownloadFile('https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe', 'python_setup.exe')"
echo [*] Running Python installer (this may take a minute)...
python_setup.exe /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
del python_setup.exe >nul 2>&1
set "PATH=%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;%PATH%"
set "PY_CMD=python"

:python_found
echo [*] Python found: !PY_CMD!
!PY_CMD! --version

REM ------------------------------------------------------------------------------
REM 2. Create Virtual Environment (.venv)
REM ------------------------------------------------------------------------------
if not exist ".venv\Scripts\python.exe" (
    echo.
    echo [*] Creating virtual environment in .venv ...
    !PY_CMD! -m venv .venv
    if !errorlevel! neq 0 (
        echo [!] ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [*] Virtual environment created successfully.
) else (
    echo [*] Virtual environment already exists - skipping creation.
)

REM ------------------------------------------------------------------------------
REM 3. Upgrade pip and install all dependencies
REM ------------------------------------------------------------------------------
echo.
echo [*] Upgrading pip, setuptools, wheel...
".venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel --quiet

echo [*] Installing all project dependencies (this may take several minutes)...
".venv\Scripts\pip.exe" install -e .
if %errorlevel% neq 0 (
    echo [!] ERROR: Dependency installation failed. Check internet connection.
    pause
    exit /b 1
)

REM ------------------------------------------------------------------------------
REM 4. Install Playwright browser (Chromium)
REM ------------------------------------------------------------------------------
echo.
echo [*] Setting up Playwright browser (Chromium)...
".venv\Scripts\playwright.exe" install chromium >nul 2>&1
if %errorlevel% equ 0 (
    echo [*] Playwright Chromium installed.
) else (
    echo [!] Playwright browser install failed - web features may be limited.
)

REM ------------------------------------------------------------------------------
REM 5. Create .env from template if missing
REM ------------------------------------------------------------------------------
if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo [*] Created .env from template. Edit it to add your API keys.
    )
)

REM Add Windows encoding fix to .env if not present
findstr /c:"PYTHONUTF8" ".env" >nul 2>&1
if %errorlevel% neq 0 (
    echo. >> ".env"
    echo PYTHONUTF8=1 >> ".env"
    echo PYTHONIOENCODING=utf-8 >> ".env"
)

REM ------------------------------------------------------------------------------
REM 6. Set up global 'gdr' command
REM ------------------------------------------------------------------------------
echo.
echo [*] Setting up global 'gdr' command...

REM Place bat in WindowsApps (already on PATH in Windows 10/11)
if exist "%LOCALAPPDATA%\Microsoft\WindowsApps" (
    (
        echo @echo off
        echo set PYTHONUTF8=1
        echo set PYTHONIOENCODING=utf-8
        echo call "%~dp0run.bat" %%*
    ) > "%LOCALAPPDATA%\Microsoft\WindowsApps\gdr.bat"
    (
        echo @echo off
        echo set PYTHONUTF8=1
        echo set PYTHONIOENCODING=utf-8
        echo call "%~dp0run.bat" %%*
    ) > "%LOCALAPPDATA%\Microsoft\WindowsApps\gdr.cmd"
)

REM Place in %USERPROFILE%\bin as backup
if not exist "%USERPROFILE%\bin" mkdir "%USERPROFILE%\bin"
(
    echo @echo off
    echo set PYTHONUTF8=1
    echo set PYTHONIOENCODING=utf-8
    echo call "%~dp0run.bat" %%*
) > "%USERPROFILE%\bin\gdr.bat"

REM Add %USERPROFILE%\bin to user PATH if not already there
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$p = [Environment]::GetEnvironmentVariable('Path','User'); if ($p -notlike '*%USERPROFILE%\bin*') { [Environment]::SetEnvironmentVariable('Path', $p + ';%USERPROFILE%\bin', 'User') }" >nul 2>&1

REM Set up PowerShell profile for 'gdr' function (overrides Get-PSDrive alias)
REM Write a helper PS1 script first, then run it - avoids CMD line-continuation issues
(
    echo $profileContent = "if (Get-Alias gdr -ErrorAction SilentlyContinue) { Remove-Item Alias:gdr -Force }"
    echo $profileContent += "`nfunction gdr { ^& '%~dp0run.bat' @args }"
    echo $targets = @(
    echo     "$env:USERPROFILE\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1",
    echo     "$env:USERPROFILE\Documents\PowerShell\Microsoft.PowerShell_profile.ps1"
    echo )
    echo foreach ($p in $targets) {
    echo     $dir = Split-Path $p -Parent
    echo     if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force ^| Out-Null }
    echo     Set-Content -Path $p -Value $profileContent -Force
    echo }
    echo Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
) > "%TEMP%\_gdr_profile_setup.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File "%TEMP%\_gdr_profile_setup.ps1" >nul 2>&1
del "%TEMP%\_gdr_profile_setup.ps1" >nul 2>&1

echo [*] 'gdr' command registered for CMD and PowerShell.

REM ------------------------------------------------------------------------------
REM 7. Download OpenWakeWord models (optional, runs in background)
REM ------------------------------------------------------------------------------
echo.
echo [*] Downloading wake word models (hey_jarvis, alexa)...
".venv\Scripts\python.exe" -c "import openwakeword.utils; openwakeword.utils.download_models()" >nul 2>&1
echo [*] Wake word models ready.

REM Fix permissions on ONNX model files
cmd /c "icacls "".venv\Lib\site-packages\openwakeword\resources\models"" /grant %USERNAME%:F /T /Q" >nul 2>&1

REM ------------------------------------------------------------------------------
REM Done!
REM ------------------------------------------------------------------------------
echo.
echo ==================================================================
echo  Installation Complete!
echo ==================================================================
echo.
echo  - Run the assistant:  double-click run.bat
echo  - From any terminal:  type 'gdr' and press Enter
echo  - Dashboard URL:      http://127.0.0.1:8844
echo.
echo  IMPORTANT: Add your Sarvam API key to .env:
echo    SARVAM_API_KEY=your_key_here
echo  Get a free key at: https://dashboard.sarvam.ai/
echo.
echo ==================================================================
pause
