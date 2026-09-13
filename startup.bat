@ECHO OFF
SETLOCAL

cd /d "%~dp0"

IF NOT EXIST "..\.venv\Scripts\activate.bat" (
    ECHO Virtual environment not found.
    ECHO Create one with: py -m venv .venv
    ECHO Then install dependencies with: pip install -r requirements.txt
    EXIT /B 1
)

CALL "..\.venv\Scripts\activate.bat"

python -c "import django" >NUL 2>&1
IF ERRORLEVEL 1 (
    ECHO Django is not installed in .venv.
    ECHO Install dependencies with: pip install -r requirements.txt
    EXIT /B 1
)

python manage.py runserver 0.0.0.0:8000

PAUSE
