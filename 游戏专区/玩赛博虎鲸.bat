@echo off
chcp 65001 >nul
title Cyber Orca Pet
for %%f in ("%~dp0*.py") do python "%%f"
echo.
echo --------------------------------------------------
echo   The whale swam back into the deep sea. Bye ~
echo --------------------------------------------------
pause
