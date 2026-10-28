@echo off
chcp 65001 >nul
rem Opens the office. Keep this window open while you use it; close it to stop.
cd /d "%~dp0"
set PORT=8765
where py >nul 2>nul && (set PY=py -3) || (set PY=python)
%PY% --version >nul 2>nul || (
  echo Python 3 was not found. Install it from https://www.python.org/downloads/ and run this again.
  echo לא נמצא Python 3. אפשר להתקין מ-https://www.python.org/downloads/ ולהריץ שוב.
  pause
  exit /b 1
)
start "" http://127.0.0.1:%PORT%
%PY% server.py %PORT%
pause
