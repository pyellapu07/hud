@echo off
:: Right-click this file and "Run as Administrator"

schtasks /Create /TN "PersonalOS Widget" /TR "\"C:\Users\prade\AppData\Local\Programs\Python\Python314\pythonw.exe\" \"F:\agra_rfbs_training-main\personal_os\widget.py\"" /SC ONLOGON /DELAY 0000:10 /RL LIMITED /F

if %ERRORLEVEL%==0 (
    echo.
    echo Success! Widget will launch 10 seconds after every login.
) else (
    echo Failed. Make sure you right-clicked and chose "Run as Administrator".
)
pause
