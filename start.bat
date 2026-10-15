@echo off
title Personal OS

:: Find Python
set "PY="
where py     >nul 2>&1 && set "PY=py"
where python >nul 2>&1 && if not defined PY set "PY=python"
for /d %%d in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
    if exist "%%d\python.exe" if not defined PY set "PY=%%d\python.exe"
)

if not defined PY (
    echo Python not found. Please install Python from python.org
    pause & exit /b 1
)

:: Pick a free port
set PORT=7777

:: Kill anything on that port
for /f "tokens=5" %%p in ('netstat -aon ^| findstr ":%PORT% " 2^>nul') do taskkill /f /pid %%p >nul 2>&1

:: Start server in background
echo Starting Personal OS on http://localhost:%PORT% ...
start /b "" "%PY%" -m http.server %PORT% --directory "%~dp0" >nul 2>&1

:: Wait a moment then open browser
timeout /t 1 /nobreak >nul
start "" "http://localhost:%PORT%"

echo.
echo  Personal OS is running at http://localhost:%PORT%
echo  Close this window to stop the server.
echo.
pause
