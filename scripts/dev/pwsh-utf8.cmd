@echo off
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set LC_ALL=C.UTF-8
set LANG=C.UTF-8
chcp 65001 >NUL
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0utf8.ps1" %*
exit /b %ERRORLEVEL%
