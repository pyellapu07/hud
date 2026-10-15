@echo off
:: Adds Personal OS widget to Windows startup

set "PS=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
set "SCRIPT=%~dp0widget.py"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "LNK=%STARTUP%\PersonalOS.lnk"

:: Find pythonw
set "PYW=pythonw"
for /d %%d in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
    if exist "%%d\pythonw.exe" set "PYW=%%d\pythonw.exe"
)

"%PS%" -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell;" ^
  "$s  = $ws.CreateShortcut('%LNK%');" ^
  "$s.TargetPath      = '%PYW%';" ^
  "$s.Arguments       = '\"%SCRIPT%\"';" ^
  "$s.WorkingDirectory= '%~dp0';" ^
  "$s.WindowStyle     = 1;" ^
  "$s.Save()"

if exist "%LNK%" (
    echo Done! Personal OS will now launch automatically on startup.
) else (
    echo Failed. Creating shortcut manually instead...
    :: Fallback: copy run bat to startup folder
    copy "%~dp0open.bat" "%STARTUP%\PersonalOS.bat" >nul
    if exist "%STARTUP%\PersonalOS.bat" (
        echo Done via fallback! open.bat added to startup.
    ) else (
        echo Still failed. Manually copy open.bat to: %STARTUP%
    )
)
pause
