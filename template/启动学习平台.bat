@echo off
chcp 65001 >nul
title 学习平台启动器
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set "PY=python"
where python >nul 2>nul
if errorlevel 1 (
  set "PY=py -3"
)
echo.
echo   正在启动学习平台，请稍候…
echo.
%PY% "%~dp0scripts\launcher.py"
echo.
echo   服务已停止，按任意键关闭窗口。
pause >nul
