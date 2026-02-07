@echo off

cd /d "%~dp0"
pyinstaller --clean --noconfirm main.spec