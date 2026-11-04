@echo off
REM Build iPhone Photo Import for Windows. Requires Python 3.10+ (python.org) and optionally Inno Setup 6.5+.
REM Output: dist\iPhonePhotoImport-Windows-Portable.zip and dist\iPhonePhotoImport-Windows-Setup.exe
setlocal
cd /d "%~dp0"

if not exist .venv-win (
    python -m venv .venv-win || goto :error
)
call .venv-win\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller || goto :error

pyinstaller --noconfirm --clean --distpath dist --workpath build build_tools\iphone_photo_import.spec || goto :error

if exist dist\iPhonePhotoImport-Windows-Portable.zip del dist\iPhonePhotoImport-Windows-Portable.zip
powershell -NoProfile -Command "Compress-Archive -Path 'dist\iPhonePhotoImport' -DestinationPath 'dist\iPhonePhotoImport-Windows-Portable.zip'" || goto :error
echo  Portable: dist\iPhonePhotoImport-Windows-Portable.zip

set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist %ISCC% (
    if defined APP_VERSION (
        %ISCC% /DAppVersion=%APP_VERSION% build_tools\installer.iss || goto :error
    ) else (
        %ISCC% build_tools\installer.iss || goto :error
    )
    echo  Installer: dist\iPhonePhotoImport-Windows-Setup.exe
) else (
    echo  Inno Setup not found - skipping installer. Get it from https://jrsoftware.org/isdl.php
)
exit /b 0

:error
echo Build failed.
exit /b 1
