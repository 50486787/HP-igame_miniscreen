@echo off
cd /d "%~dp0"
python hook.py %*
exit /b %errorlevel%
