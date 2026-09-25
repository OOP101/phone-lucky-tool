@echo off
rem ASCII-only launcher: safe on any codepage. Chinese output comes from Python (UTF-8).
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set "PYTHONIOENCODING=utf-8"

set "PY=python"
where py >nul 2>nul
if %errorlevel%==0 set "PY=py"

"%PY%" scripts\build_all.py %*
if errorlevel 1 (
  echo.
  echo [FAILED] build finished with errors, see above.
) else (
  echo.
  echo [OK] all resume files rebuilt -^> output\
)
pause
