@echo off
chcp 65001 >nul
title Push Gallery to GitHub
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0push.ps1"
echo.
pause >nul
