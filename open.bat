@echo off
:: Launch Personal OS widget (no console window)
set "WIDGET=%~dp0widget.py"
set "PYW="

:: Scan standard install locations first
for /d %%d in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%d\pythonw.exe" if not defined PYW set "PYW=%%d\pythonw.exe"
)
for /d %%d in ("C:\Python3*") do (
    if exist "%%d\pythonw.exe" if not defined PYW set "PYW=%%d\pythonw.exe"
)
:: Fallback: pythonw on PATH
if not defined PYW (
    where pythonw >nul 2>&1 && set "PYW=pythonw"
)
:: Fallback: derive from python on PATH
if not defined PYW (
    for /f "delims=" %%p in ('where python 2^>nul') do (
        if not defined PYW for %%F in ("%%p") do (
            if exist "%%~dpFpythonw.exe" set "PYW=%%~dpFpythonw.exe"
        )
    )
)

if not defined PYW (
    echo Python not found. Run setup.bat first.
    pause & exit /b 1
)

start "" "%PYW%" "%WIDGET%"
