@echo off
chcp 65001 >nul
title 课程平台 Bot
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0launcher_gui.ps1"
if errorlevel 1 pause
