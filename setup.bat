@echo off
title Personal OS — Setup
echo.
echo  ================================================
echo   Personal OS  ^|  First-time Setup
echo  ================================================
echo.

:: ── 1. Find Python ─────────────────────────────────────────────────────────────
set "PY="
set "PYW="

:: Use PATH-based python first (respects the user's chosen default version)
for /f "delims=" %%p in ('where python 2^>nul') do (
    if not defined PY (
        set "PY=%%p"
        for %%F in ("%%p") do (
            if exist "%%~dpFpythonw.exe" set "PYW=%%~dpFpythonw.exe"
        )
    )
)

:: Fallback: scan by explicit version order, newest first
for %%v in (314 313 312 311 310 39 38) do (
    if not defined PY (
        if exist "%LOCALAPPDATA%\Programs\Python\Python%%v\python.exe" (
            set "PY=%LOCALAPPDATA%\Programs\Python\Python%%v\python.exe"
            set "PYW=%LOCALAPPDATA%\Programs\Python\Python%%v\pythonw.exe"
        )
    )
)

if not defined PYW if defined PY set "PYW=pythonw"

if not defined PY (
    echo [ERROR] Python not found.
    echo         Install Python 3.10+ from https://python.org
    echo         Tick "Add Python to PATH" during install, then re-run setup.bat
    echo.
    pause & exit /b 1
)

echo Found Python : %PY%
echo Found pythonw: %PYW%
echo.

:: ── 2. Install dependencies ───────────────────────────────────────────────────
echo Installing dependencies...
"%PY%" -m pip install --upgrade --quiet ^
    customtkinter ^
    google-auth ^
    google-auth-oauthlib ^
    google-auth-httplib2 ^
    google-api-python-client

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] pip install failed. Check your internet connection and try again.
    pause & exit /b 1
)
echo Dependencies installed successfully.
echo.

:: ── 3. Task Scheduler — auto-launch at Windows login ─────────────────────────
echo Setting up auto-launch on login...
set "WIDGET=%~dp0widget.py"
set "TASK=PersonalOSWidget"

:: /F silently overwrites any existing task with the same name
schtasks /Create /F /TN "%TASK%" /SC ONLOGON /DELAY 0000:15 /RL LIMITED ^
    /TR "\"%PYW%\" \"%WIDGET%\"" >nul 2>&1

if %errorlevel% equ 0 (
    echo Auto-launch configured — widget starts 15s after every login.
) else (
    echo [WARN] Could not create scheduled task.
    echo        Run setup.bat as Administrator for auto-launch support.
    echo        You can still open the widget manually with open.bat.
)
echo.

:: ── 4. Remind about credentials.json ─────────────────────────────────────────
if not exist "%~dp0credentials.json" (
    echo [NOTE] credentials.json not found.
    echo        Google Calendar and Gmail sync require your own OAuth credentials.
    echo        See README.md for the 5-minute setup guide.
    echo.
)

:: ── 5. Launch ─────────────────────────────────────────────────────────────────
echo Launching Personal OS...
start "" "%PYW%" "%WIDGET%"
echo.
echo Setup complete! The widget will open shortly.
echo.
pause
