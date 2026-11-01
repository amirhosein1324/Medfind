@echo off
setlocal
REM Runs the crawler on Windows itself (not in Docker), so it uses the same
REM network as your web browser. Needs Python 3.10+ and `docker compose up -d db`.
cd /d "%~dp0"
if not exist .venv ( python -m venv .venv )
call .venv\Scripts\activate.bat

python -c "import sqlalchemy, psycopg2, pydantic_settings, httpx" 2>nul
if %errorlevel%==0 goto run

echo Installing the few packages the crawler needs (slow connections: this can take a while)...
REM Try the default index first, then mirrors that are usually faster from Iran.
for %%I in ("https://pypi.org/simple" "https://mirror-pypi.runflare.com/simple" "https://package-mirror.liara.ir/repository/pypi/simple" "https://pypi.tuna.tsinghua.edu.cn/simple") do (
  echo Trying %%~I
  pip install --default-timeout=120 --retries 8 -i %%~I -r requirements-crawler.txt
  python -c "import sqlalchemy, psycopg2, pydantic_settings, httpx" 2>nul
  if not errorlevel 1 goto run
)
echo.
echo Could not install the packages. Check your internet/VPN and run this file again,
echo or run:  pip install --default-timeout=300 -r requirements-crawler.txt
pause
exit /b 1

:run
set DATABASE_URL=postgresql+psycopg2://medfind:medfind@localhost:5432/medfind
echo Checking which sites are reachable from this computer...
python -m scripts.check_sites
echo.
echo Starting the crawler (Ctrl+C to stop). Results appear in Admin ^> Data sources.
python -m scripts.crawl --loop --every 6
