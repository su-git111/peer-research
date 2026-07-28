@echo off
cd /d "%~dp0"
set "PY=py"
where py >nul 2>nul || set "PY=python"
%PY% cowork.py menu
if errorlevel 1 pause
