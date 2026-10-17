@echo off
REM Runs the crawler on Windows itself (not in Docker), so it uses the same
REM network as your web browser. Needs Python 3.10+ and `docker compose up -d db`.
cd /d "%~dp0"
if not exist .venv (
  python -m venv .venv
)
call .venv\Scripts\activate.bat
pip install -q -r requirements.txt
set DATABASE_URL=postgresql+psycopg2://medfind:medfind@localhost:5432/medfind
echo Checking which sites are reachable from this computer...
python -m scripts.check_sites
echo.
echo Starting the crawler (Ctrl+C to stop). Results appear in Admin ^> Data sources.
python -m scripts.crawl --loop --every 6
