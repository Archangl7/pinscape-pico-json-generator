@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 pinscape_builder.py
) else (
    python pinscape_builder.py
)
if errorlevel 1 (
    echo.
    echo The builder could not start. Python 3 may need to be installed.
    pause
)
