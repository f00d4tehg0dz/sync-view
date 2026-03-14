@echo off
echo ============================================
echo  Sync View - Build Script
echo ============================================
echo.

:: Check Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python not found in PATH.
    pause
    exit /b 1
)

:: Install dependencies (including PyInstaller)
echo Installing dependencies...
python -m pip install -r native-host\requirements.txt
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo [1/3] Building host.exe (native messaging host)...
python -m PyInstaller --noconfirm --onefile --console ^
    --name "host" ^
    --distpath "dist" ^
    native-host\host.py
if %errorlevel% neq 0 (
    echo ERROR: Failed to build host.exe
    pause
    exit /b 1
)

echo.
echo [2/3] Building SyncView.exe (desktop app)...
python -m PyInstaller --noconfirm --onefile --windowed ^
    --name "SyncView" ^
    --icon "icons\icon.ico" ^
    --add-data "icons\icon-48.png;." ^
    --distpath "dist" ^
    native-host\app.py
if %errorlevel% neq 0 (
    echo ERROR: Failed to build SyncView.exe
    pause
    exit /b 1
)

echo.
echo [3/3] Packaging Firefox extension...
if not exist "dist\extension" mkdir "dist\extension"
copy manifest.json "dist\extension\" >nul
copy content.js "dist\extension\" >nul
copy background.js "dist\extension\" >nul
xcopy /E /I /Y popup "dist\extension\popup" >nul
xcopy /E /I /Y icons "dist\extension\icons" >nul

:: Build .xpi (zip archive with .xpi extension)
if exist "dist\sync-view.xpi" del "dist\sync-view.xpi"
where tar >nul 2>nul
if %errorlevel% equ 0 (
    pushd dist\extension
    tar -a -cf ..\sync-view.zip *
    popd
    move "dist\sync-view.zip" "dist\sync-view.xpi" >nul
    echo Extension packaged: dist\sync-view.xpi
) else (
    echo WARNING: tar not found. Skipping .xpi packaging.
    echo You can manually zip the contents of dist\extension\ and rename to .xpi
)

echo.
echo ============================================
echo  Build complete!
echo  Output: dist\SyncView.exe
echo          dist\host.exe
echo          dist\extension\
echo          dist\sync-view.xpi
echo ============================================
pause
