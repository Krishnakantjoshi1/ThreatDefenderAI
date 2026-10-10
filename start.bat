@echo off
REM ThreatDefender AI - one-click start (Windows)
cd /d "%~dp0"
if not exist venv (
  echo Creating virtual environment...
  python -m venv venv
)
call venv\Scripts\activate
echo Installing requirements...
pip install -q -r requirements.txt
python desktop\launcher.py
pause
