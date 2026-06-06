@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    py -3 -m venv .venv
    .venv\Scripts\pip install -r requirements.txt
)
call .venv\Scripts\activate.bat
python main.py
pause
