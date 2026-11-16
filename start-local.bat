@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo CONGLOMERATE v0.4 - local offline server on 127.0.0.1:8765
echo Open in your browser: http://127.0.0.1:8765/index.html
where py >nul 2>&1
if %errorlevel%==0 (
    py -m http.server 8765 --bind 127.0.0.1
) else (
    where python >nul 2>&1
    if %errorlevel%==0 (
        python -m http.server 8765 --bind 127.0.0.1
    ) else (
        echo Python is not installed. You may open the HTML file directly.
        echo For safe and portable saves, export JSON backups regularly.
        pause
    )
)
