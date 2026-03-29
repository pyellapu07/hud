@echo off
:: Launch Personal OS widget (no console window)
set "WIDGET=%~dp0widget.py"
set "PYW="

:: Try PATH-based python first (user's default version, most reliable)
for /f "delims=" %%p in ('where python 2^>nul') do (
    if not defined PYW for %%F in ("%%p") do (
        if exist "%%~dpFpythonw.exe" set "PYW=%%~dpFpythonw.exe"
    )
)

:: Fallback: scan by explicit version order, newest first
for %%v in (314 313 312 311 310 39 38) do (
    if not defined PYW (
        if exist "%LOCALAPPDATA%\Programs\Python\Python%%v\pythonw.exe" (
            set "PYW=%LOCALAPPDATA%\Programs\Python\Python%%v\pythonw.exe"
        )
    )
)

if not defined PYW (
    echo Python not found. Run setup.bat first.
    pause & exit /b 1
)

start "" "%PYW%" "%WIDGET%"
