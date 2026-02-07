@echo off
setlocal

cd /d "%~dp0"

REM Ensure pip is available and up to date
python -m pip install --upgrade pip >nul

if exist requirements.txt (
  pip install -r requirements.txt
)

pip install pyinstaller

REM Clean + build with spec
pyinstaller --clean --noconfirm main.spec

endlocal