@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py"
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo Python was not found on this computer.
        echo Build the EXE on the same computer where Start Pinscape Builder.bat works.
        pause
        exit /b 1
    )
    set "PY=python"
)

echo Installing or updating the Windows packaging tool...
%PY% -m pip install --upgrade pyinstaller
if errorlevel 1 goto :failed

echo Building PinscapePicoJSONGenerator.exe...
%PY% -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name PinscapePicoJSONGenerator ^
    --add-data "assets;assets" ^
    pinscape_builder.py
if errorlevel 1 goto :failed

echo.
echo Build complete:
echo %CD%\dist\PinscapePicoJSONGenerator.exe
explorer "%CD%\dist"
pause
exit /b 0

:failed
echo.
echo The Windows EXE build failed. Review the messages above.
pause
exit /b 1
